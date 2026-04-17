from pathlib import Path
from dotenv import load_dotenv
import os
import sys
import argparse

# Load environment variables from .env in the same directory as agent.py
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Parse authentication flags
parser = argparse.ArgumentParser(description="Run S.I.G.H.T. Report Agent")
parser.add_argument("--user", action="store_true", help="Use Application Default Credentials (interactive login)")
parser.add_argument("--service", action="store_true", help="Use Service Account key from .env")
# Parse only known args to avoid conflicts with tool/agent internal arguments if any
args, _ = parser.parse_known_args()

# Logic: Default to --user unless --service is specifically requested
if args.service:
    print("🔐 [AUTH] Mode: SERVICE ACCOUNT")
    # Normalize Google Credentials path to be absolute
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        if not os.path.isabs(creds_path):
            root_dir = Path(__file__).resolve().parent.parent
            abs_creds_path = str(root_dir / creds_path)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds_path
            print(f"DEBUG: Normalized GOOGLE_APPLICATION_CREDENTIALS to: {abs_creds_path}")
else:
    print("👤 [AUTH] Mode: USER ADC (Default)")
    # Remove the env var if it exists to force fallback to ADC
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

import sys, os, json
import asyncio

# Add directories to sys.path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(parent_dir) + "/tools")

from pyairtable import Api
from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import DiscoveryEngineSearchTool
from bigquery.agent import bq_analyst, get_table_schema, run_bigquery_query, fetch_report_pipelines
from typing import List, Dict, Any
from vertexai.generative_models import GenerativeModel, Part, Image
from firestore_utils import get_latest_instruction

try:
    from course_search import EnhancedCourseSearchTool
    from infographic import generate_trip_infographic, process_gcs_manifest_tool, save_report_as_pdf, save_to_bucket, create_and_share_google_doc, save_text_report_to_gcs, save_report_as_word, upload_file_to_drive
except ImportError:
    from tools import EnhancedCourseSearchTool, generate_trip_infographic, process_gcs_manifest_tool, save_report_as_pdf, save_to_bucket, create_and_share_google_doc, save_text_report_to_gcs, save_report_as_word, upload_file_to_drive

# Environment already loaded above

# --- Specialized Instructions ---

BQ_INSTRUCTION = """You are a BigQuery Data Expert.
Your goal is to fetch the survey data for the provided client/company name.
1. Call the `fetch_report_pipelines` tool to get the survey data.
2. Output a structured summary of the data, specifically focusing on the 'company' and 'classes' (date, instructor, title, attendees).
3. Ensure the output format is clear so the next stage can analyze it correctly.
Example output format:
{
    "company": "Rackspace",
    "classes": [
        {"date": "Jan 1, 2026", "instructor": "Joey Gagliardo", "title": "Advanced AI", "attendees": 15}
    ]
}
"""

BODY_INSTRUCTION = """You are an insightful data analyst. You will receive survey data retrieved from BigQuery.
    
Analyze the q1, q2 and q3 fields (Content Calibration, Client Projects, Strategic Recommendations) from the provided data.

* Analysis Requirements:
  - Summarize content gaps ("Content Calibration & Gaps - Watchpoint").
  - Identify future tech initiatives ("Client Projects & Tech Initiatives").
  - Highlight strategic recommendations for deeper training.

* Course Search:
  - Distill technical themes into search keywords.
  - Use `EnhancedCourseSearchTool` to find relevant course outlines.
  - Recommended courses should be formatted as hyperlinks: `[Full Course Title](DOCUMENT_URL)`.

Produce a comprehensive text-only report. Do not include raw data or mention "Yes/NA" responses.
"""

GRAPHIC_INSTRUCTION = """You are a report designer. You will receive survey data retrieved from BigQuery.
Your ONLY job is to call the `generate_trip_infographic` tool using the 'company' and 'classes' data provided.
Once the infographic is generated, output the local path to the generated image file.
"""

FINALIZER_INSTRUCTION = f"""You are the CRITICAL FINAL STAGE of the S.I.G.H.T. report pipeline.
You will receive:
1. A comprehensive text analysis report (from the body_agent).
2. The result object from the graphic_agent (containing path and metadata).

Your MANDATORY tasks are:
1. Call the `create_and_share_google_doc` tool to create a native Google Doc.
   - Note: The tool will automatically use the correct destination folder.
   - Pass the result object from the graphic_agent (received in input 2) as 'image_object'.

CONDITIONAL TASKS (Only if the user explicitly asks to "store" or "save" formal files):
- Call `save_report_as_word` to generate a .docx file.
- Call `save_to_bucket` to upload the Word document and the infographic PNG to GCS.
- Call `save_text_report_to_gcs` to save the raw text analysis.
- Call `upload_file_to_drive` to upload the Word document to Google Drive.
- Call `save_report_as_pdf` if a PDF was specifically requested.

DO NOT perform the conditional archival steps unless the user explicitly requested them in their prompt.

FINAL RESPONSE FORMATting:
You MUST structure your final response as follows:
[[INFOGRAPHIC:reports/actual_infographic_filename.png]]

# Analysis Report for [CompanyName]
[Full Report Body Text]

[Link to Google Doc on Google Drive]

IMPORTANT: Omit all other technical summaries, GCS paths, or Word document links. Focus only on the three items above.

DO NOT just summarize. You MUST call the mandatory tools to complete the pipeline.
Finally, provide a summary with the GCS links AND the Google Drive links for both the Word document and the native Google Doc.
"""

# --- Define the Agents ---

# Stage 1: Data Retrieval
bq_agent = Agent(
    name="bq_agent",
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    instruction=BQ_INSTRUCTION,
    tools=[fetch_report_pipelines, get_table_schema, run_bigquery_query]
)

# Stage 2: Parallel Analysis & Graphic Generation
body_agent = Agent(
    name="body_agent",
    model=os.environ.get("MODEL", "gemini-2.5-flash"), 
    instruction=BODY_INSTRUCTION,
    tools=[
        EnhancedCourseSearchTool(
            data_store_id="projects/roitraining-dashboard/locations/global/collections/default_collection/dataStores/gcp-course-outlines", 
            location="global"
        )
    ],
)

graphic_agent = Agent(
    name="graphic_agent",
    model=os.environ.get("MODEL", "gemini-2.5-flash"), 
    instruction=GRAPHIC_INSTRUCTION,
    tools=[generate_trip_infographic],
)

parallel_orchestrator = ParallelAgent(
    name="parallel_orchestrator",
    sub_agents=[body_agent, graphic_agent]
)

# Stage 3: Consolidation
pdf_finalizer = Agent(
    name="pdf_finalizer",
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    instruction=FINALIZER_INSTRUCTION,
    tools=[save_report_as_pdf, save_report_as_word, save_to_bucket, create_and_share_google_doc, save_text_report_to_gcs, upload_file_to_drive]
)

# --- Orchestrate the Full Pipeline ---
sight_agent = SequentialAgent(
    name="sight_agent",
    sub_agents=[bq_agent, parallel_orchestrator, pdf_finalizer]
)

root_agent = sight_agent

if __name__ == "__main__":
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    async def main():
        print("🚀 [TEST] Running agent with prompt: 'Do Rackspace'...")
        
        # Initialize a local runner for testing
        runner = Runner(
            app_name="sight_report_test",
            agent=sight_agent,
            session_service=InMemorySessionService(),
            auto_create_session=True
        )
        
        # Runner handles context initialization and event streaming
        agen = runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(parts=[types.Part(text="Do Rackspace")])
        )
        
        final_response = ""
        async for event in agen:
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        # print(part.text, end="", flush=True)
                        final_response += part.text
        
        print("\n--- FINAL AGENT RESPONSE ---")
        if final_response:
            print(final_response)
        else:
            print("No text response received. (Check if tools were called successfully)")
        print("----------------------------")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ [TEST] Error running agent: {e}")
        import traceback
        traceback.print_exc()
