import os
import asyncio
import sys
import json
from pathlib import Path

# Add directories to sys.path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pyairtable import Api
from google.adk.agents import Agent
from google.adk.tools import DiscoveryEngineSearchTool
from bigquery.agent import bq_analyst, get_table_schema, run_bigquery_query, fetch_report_pipelines
try:
    from .tools import EnhancedCourseSearchTool, generate_trip_infographic, process_gcs_manifest_tool, save_report_as_pdf, save_to_bucket
except ImportError:
    from tools import EnhancedCourseSearchTool, generate_trip_infographic, process_gcs_manifest_tool, save_report_as_pdf, save_to_bucket

from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, Part, Image
from firestore_utils import get_latest_instruction
from dotenv import load_dotenv

load_dotenv()

# --- Fetch Instructions ---
_fetched_instruction = get_latest_instruction("sight_report_analyst")

FALLBACK_INSTRUCTION = """You are an insightful data analyst processing client feedback.
    
Call the `fetch_report_pipelines` tool to get the survey data for the provided client/company name, and optionally a date range if requested.
When referring to q1, q2, q3 use the fields: q1_content_calibration_and_gaps, q2_client_projects_and_tech_initiatives, q3_strategic_recommendat, respectively.
Fetch the q1, q2 and q3, the istunum from the result data.

* Do not include the raw data in the output

* Avoid saying something like the quote/unquote "Yes" or "N/A" responses.

* For any of the paragraphs below if there is no relevant data, keep it short.

* Use the generate_trip_infographic tool to generate an infographic of the classes. Display the infographic in the output at the top followed by the report you generate below:

* Format the output of fetch_report_pipelines tools to look like this example to pass to the generate_trip_inforgraphic tool
 {
        "company": "Rackspace",
        "classes": [
            {"date": "Jan 1, 2026", "instructor": "Joey Gagliardo", "title": "Advanced Generative AI and Large Language Model Development Workshop for Enterprise Applications and Business Transformation", "attendees": 15},
            {"date": "Feb 1, 2026", "instructor": "Doug Rehnstrom", "title": "Google ADK Supercalifragilistic Expialidocious", "attendees": 20}
            ]
            }

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
    - If no course-specific document URL is provided by the tool, do not include a hyperlink for that specific item.

* **Final Step: Save and Upload Complete Report**
  - Once you have generated the full text of the report (Infographic, Content Calibration, Initiatives, Strategic Recommendations, and Follow-on Opportunities):
    1. Call the `save_report_as_pdf` tool with the text, company name, and infographic path. This will return a local file path.
    2. Call the `save_to_bucket` tool with that local file path to save it to the cloud storage bucket `roitraining-dashboard-grounding` in a folder called reports.
  - Inform the user that the complete report has been finalized and uploaded to GCS, providing the resulting GCS path.
"""

# Instruction processing logic
if _fetched_instruction:
    print(f"🚀 [INIT] Successfully fetched latest instructions from Firestore for 'sight_report_analyst'")
    instruction_text = _fetched_instruction
else:
    print(f"⚠️ [INIT] Firestore fetch failed or empty. Using FALLBACK_INSTRUCTION.")
    instruction_text = FALLBACK_INSTRUCTION

# --- Define the Agent ---
sight_agent = Agent(
    name="sight_reader",
    model=os.getenv("MODEL", "gemini-2.0-flash"), 
    instruction=instruction_text,

    tools=[
        generate_trip_infographic,
        EnhancedCourseSearchTool(
            data_store_id="projects/roitraining-dashboard/locations/global/collections/default_collection/dataStores/gcp-course-outlines", 
            location="global"
        ), 
        fetch_report_pipelines,
        process_gcs_manifest_tool,
        save_report_as_pdf,
        save_to_bucket
    ],
)

root_agent = sight_agent

if __name__ == "__main__":
    async def main():
        print("🚀 [TEST] Running agent with prompt: 'Do Rackspace'...")
        response = await sight_agent.run_async("Do Rackspace")
        print("\n--- AGENT RESPONSE ---")
        print(response.text if hasattr(response, 'text') else response)
        print("----------------------")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ [TEST] Error running agent: {e}")
