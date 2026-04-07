import os
import asyncio
import sys
import json
from pathlib import Path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from pyairtable import Api
from google.adk.agents import Agent
from google.adk.tools import DiscoveryEngineSearchTool
from bigquery.agent import bq_analyst, get_table_schema, run_bigquery_query, fetch_report_pipelines

from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, Part, Image

from .tools import EnhancedCourseSearchTool
from firestore_utils import get_latest_instruction

from dotenv import load_dotenv

load_dotenv()

def process_gcs_manifest_tool(input_json: str) -> str:
    """
    Parses a manifest of names and GCS paths, downloads the images,
    and sends them to Gemini for multimodal processing.
    
    Args:
        input_json: JSON string with dynamic keys and GCS URIs.
    """
    # 1. Parse the dynamic JSON
    data: Dict[str, str] = json.loads(input_json)
    
    multimodal_parts: List[Any] = []
    
    # 2. Iterate through the dictionary to build the prompt
    # We add instructions for the model to associate names with specific images
    multimodal_parts.append("Please process the following images. " 
                            "The first is a template, followed by specific individuals:")

    for key, gcs_uri in data.items():
        # Create a Part from the GCS URI
        # Note: mime_type detection can be automated based on file extension
        mime_type = "image/png" if gcs_uri.lower().endswith(".png") else "image/jpeg"
        image_part = Part.from_uri(uri=gcs_uri, mime_type=mime_type)
        
        # We interleave the Key Name so the model knows which image is which
        multimodal_parts.append(f"Label for next image: {key}")
        multimodal_parts.append(image_part)

    # Final instruction to the model
    multimodal_parts.append("Analyze these images and return the result.")
    return multimodal_parts


# --- Your Airtable Tool ---
# def read_airtable_table(table_name: str, columns: list[str] = None):
#     """
#     Reads records from a specified Airtable table. To save memory and context, 
#     specify only the columns you need.
    
#     Args:
#         table_name: The exact name of the table.
#         columns: A list of column names to retrieve (e.g., ['Status', 'Description']). 
#                  If None, all columns are retrieved (not recommended for large tables).
#     """
#     api_key = os.environ.get("AIRTABLE_API_KEY")
#     base_id = os.environ.get("AIRTABLE_BASE_ID")
    
#     if not (api_key and base_id):
#         return {"error": "Missing credentials"}
        
#     try:
#         api = Api(api_key)
#         target_table = api.table(base_id, table_name)
        
#         # We pass the 'fields' argument to the pyairtable call
#         # This filters the data at the API level, before it ever hits your RAM
#         records = target_table.all(fields=columns) if columns else target_table.all()
        
#         return [{"id": r["id"], "fields": r["fields"]} for r in records]
#     except Exception as e:
#         return {"error": f"Error querying {table_name}: {str(e)}"}


# --- Fetch Instructions from Firestore ---
# We store the latest instructions in Firestore database 'sight-report', collection 'prompts'
# Querying for agent_name: 'sight_report_analyst'
_fetched_instruction = get_latest_instruction("sight_report_analyst")

# Fallback instruction (the original hardcoded one) in case Firestore is empty or unreachable
FALLBACK_INSTRUCTION = """You are an insightful data analyst processing client feedback.
    
Call the `fetch_report_pipelines` tool to get the survey data for the provided client/company name, and optionally a date range if requested.
When referring to q1, q2, q3 use the fields: q1_content_calibration_and_gaps, q2_client_projects_and_tech_initiatives, q3_strategic_recommendat, respectively.
Fetch the q1, q2 and q3, the istunum from the result data.

* Do not include the raw data in the output

* Avoid saying something like the quote/unquote "Yes" or "N/A" responses.

* For any of the paragraphs below if there is no relevant data, keep it short.

* Analyze the data from the three question columns and look for any gaps in the class content and the audience expectations.
  - Write this up as a short a paragraph that summarizes any disparity between expections and what we provided. 
  - Title this paragraph with the header: "Content Calibration & Gaps - Watchpoint"

* Analyze the data for "Client Projects & Tech Initiatives"
  - Write this up as a short a paragraph that summarizes any current or future client technical initiatives or projects or technologies they are interested in.
  Title this paragraph with the header: "Client Projects & Tech Initiatives"

* Analyze the data for "Strategic Recommendations"
  - Write a short paragraph that looks for comments that refer to wanting to take a deeper dive into additional training either by 
    - having more days of training on the same subject (vertical)
    - training on a related topics, such as if someone took a class on LLM's maybe Agentic development would be a good followup (horizontal)

* **Step 4: Query Distillation & Search**
  - Based on the "Watchpoint", "Initiatives", and "Strategic Recommendations" above, distill the most critical technical themes and learning gaps into a focused search query of 5-10 technical keywords (e.g., "GKE security Anthos service mesh course outlines").
  - Use this distilled query as the `query` argument for the `EnhancedCourseSearchTool` to find the most relevant course outlines.

* In a section called "Potential Follow-on Opportunities & Next Steps" 
  - Provide a short summary paragraph of the follow-on strategy.
  - List the specific recommended courses by name and a brief 1-sentence justification for each based on the search results and the client's stated needs.
  - **HYPERLINK FORMATTING RULE (MANDATORY)**:
    - You MUST format every course recommendation as a hyperlink using the formula: `[Full Course Title](DOCUMENT_URL)`.
    - Retrieve the `DOCUMENT_URL` from the tool output's `url` field or the `SOURCE_DOCUMENT_LINK` in the content.
    - **CRITICAL**: Only use direct document links (e.g., `https://storage.googleapis.com/...`). 
    - **SHUN**: Never use generic search links like `https://cloud.google.com/training`.
    - If a GCS path (`gs://...`) is returned, convert it to its public HTTPS storage equivalent.
    - If no course-specific document URL is provided by the tool, do not include a hyperlink for that specific item.

 
"""

# Final instruction after checking Firestore
if _fetched_instruction:
    print(f"🚀 [INIT] Successfully fetched latest instructions from Firestore for 'sight_report_analyst'")
    instruction_text = _fetched_instruction
else:
    print(f"⚠️ [INIT] Firestore fetch failed or empty. Using FALLBACK_INSTRUCTION.")
    instruction_text = FALLBACK_INSTRUCTION

# --- Define the Agent ---
sight_agent = Agent(
    name="sight_reader",
    model=os.getenv("MODEL", "gemini-2.5-flash"), 
    instruction=instruction_text,

    tools=[
        EnhancedCourseSearchTool(
            data_store_id="projects/roitraining-dashboard/locations/global/collections/default_collection/dataStores/gcp-course-outlines", 
            location="global"
        ), 
        fetch_report_pipelines
        , process_gcs_manifest_tool
    ],
    # sub_agents=[bq_analyst]
)

root_agent = sight_agent

# Simple test to verify the tool works with a hardcoded name
if __name__ == "__main__":
    print("Testing tool directly...")
    # print(read_airtable_table("S.I.G.H.T. Reports"))
    # input = {"template": "gs://"
    # , "company_logo": "gs://roitraining-dashboard-grounding/company_logos/Rackspace.jpg"
    # , "Joey Gagliardo": "gs://roitraining-dashboard-grounding/instructor_photos/Joey Gagliardo.jpg"
    # , "Doug Rehnstrom": "gs://roitraining-dashboard-grounding/instructor_photos/Doug Rehnstrom.jpg"
    # }
    # print(process_gcs_manifest_tool(json.dumps(input)))


