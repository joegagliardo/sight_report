import os
import json
import sys
import base64
from pathlib import Path
from google.cloud import storage
from pathlib import Path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from typing import List, Dict, Any
from dotenv import load_dotenv
from callback_logging import log_query_to_model, log_model_response, before_tool_callback, after_tool_callback

# Load environment variables from .env file
load_dotenv()

# Force use of Vertex AI backend instead of Gemini API.
# This allows using GCP account login (ADC) instead of an API key.
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_PROJECT"] = "roitraining-dashboard"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# Purge any existing API keys to prevent the SDK from
# incorrectly trying to use them against the Vertex AI endpoint.
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("GOOGLE_API_KEY", None)

# Add parent directory to sys.path for local imports
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from google.adk.agents import Agent
from firestore_utils import get_latest_instruction
from vertexai.generative_models import Part

def fetch_gcs_image_base64(gcs_uri: str) -> str:
    """Fetches an image from GCS and returns it as a base64 data URL."""
    if not gcs_uri.startswith("gs://"):
        return gcs_uri
    
    try:
        bucket_name = gcs_uri.split("/")[2]
        blob_name = "/".join(gcs_uri.split("/")[3:])
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        image_bytes = blob.download_as_bytes()
        
        # Use Pillow to downsample image to save tokens
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Max dimension of 512px to keep token count manageable
        img.thumbnail((512, 512))
        
        # Determine MIME type and save back to bytes
        ext = blob_name.split(".")[-1].lower()
        mime_type = "image/png"
        format_str = "PNG"
        if ext in ["jpg", "jpeg"]:
            mime_type = "image/jpeg"
            format_str = "JPEG"
        elif ext == "webp":
            mime_type = "image/webp"
            format_str = "WEBP"
        
        output = io.BytesIO()
        img.save(output, format=format_str, quality=80)
        image_bytes = output.getvalue()
        
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{b64_data}"
    except Exception as e:
        print(f"Error fetching GCS image {gcs_uri}: {e}")
        return gcs_uri # Fallback to URI if fetch fails

def process_gcs_manifest_tool_images(input_json: str, base_bucket: str = "gs://roitraining-dashboard-grounding") -> str:
    """
    Parses a manifest of names and GCS paths, and returns a JSON string 
    mapping labels to their full GCS URIs exactly as requested.
    """
    import re
    base_bucket = base_bucket.rstrip('/') + '/'

    try:
        # 1. Brutal cleaning for smart quotes and other common copy-paste artifacts
        # Replace all variations of smart double quotes with standard double quotes
        clean_json = re.sub(r'[\u201C\u201D\u201E\u201F]+', '"', input_json)
        # Replace all variations of smart single quotes with standard single quotes
        clean_json = re.sub(r'[\u2018\u2019\u201A\u201B]+', "'", clean_json)
        
        # 2. Find the actual JSON block if there's surrounding text
        match = re.search(r'(\{.*\})', clean_json, re.DOTALL)
        if match:
            clean_json = match.group(1)

        data: Dict[str, Any] = json.loads(clean_json)
        
        manifest: Dict[str, str] = {}

        # 1. Process Template
        template_val = data.get("template")
        if template_val:
            # Templates are typically .png as per previous turns
            uri = f"{base_bucket}templates/{template_val}"
            manifest[template_val] = fetch_gcs_image_base64(uri)

        # 2. Process Company
        company_val = data.get("company")
        if company_val:
            # Plural 'company_logos' as confirmed in working GCS paths
            uri = f"{base_bucket}company_logos/{company_val}"
            # Try both .png and .jpg
            manifest["company_logo"] = fetch_gcs_image_base64(uri + ".png")
            # If the fetch fails to find .png, the error handling handles it

        # 3. Process Classes/Instructors
        classes = data.get("classes", [])
        if isinstance(classes, list):
            for cls_obj in classes:
                instructor = cls_obj.get("instructor")
                if instructor:
                    # Instructors seem to be .jpg in some cases
                    uri = f"{base_bucket}instructor_photos/{instructor}.jpg"
                    manifest[instructor] = fetch_gcs_image_base64(uri)

        result_str = json.dumps(manifest, indent=2)
        print(f"Tool Result: {result_str}")
        return result_str

    except Exception as e:
        error_msg = f"Error parsing JSON tools input: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg})

def process_gcs_manifest_tool(input_json: str, base_bucket: str = "gs://roitraining-dashboard-grounding") -> str:
    """
    Parses a manifest of names and GCS paths, and returns a JSON string 
    mapping labels to their full GCS URIs exactly as requested.
    """
    import re
    base_bucket = base_bucket.rstrip('/') + '/'

    try:
        # 1. Brutal cleaning for smart quotes and other common copy-paste artifacts
        # Replace all variations of smart double quotes with standard double quotes
        clean_json = re.sub(r'[\u201C\u201D\u201E\u201F]+', '"', input_json)
        # Replace all variations of smart single quotes with standard single quotes
        clean_json = re.sub(r'[\u2018\u2019\u201A\u201B]+', "'", clean_json)
        
        # 2. Find the actual JSON block if there's surrounding text
        match = re.search(r'(\{.*\})', clean_json, re.DOTALL)
        if match:
            clean_json = match.group(1)

        data: Dict[str, Any] = json.loads(clean_json)
        
        manifest: Dict[str, str] = {}

        # 1. Process Template
        template_val = data.get("template")
        if template_val:
            manifest[template_val] = f"{base_bucket}templates/{template_val}"

        # 2. Process Company
        company_val = data.get("company")
        if company_val:
            # Desired: Key='company_log', Folder='company_logo'
            manifest["company_logo"] = f"{base_bucket}company_logo/{company_val}.png"

        # 3. Process Classes/Instructors
        classes = data.get("classes", [])
        if isinstance(classes, list):
            for cls_obj in classes:
                instructor = cls_obj.get("instructor")
                if instructor:
                    # Desired: Key=Instructor Name, Folder='instructor_photos'
                    manifest[instructor] = f"{base_bucket}instructor_photos/{instructor}.png"

        result_str = json.dumps(manifest, indent=2)
        print(f"Tool Result: {result_str}")
        return result_str

    except Exception as e:
        error_msg = f"Error parsing JSON tools input: {str(e)}"
        print(error_msg)
        return json.dumps({"error": error_msg})

# --- Default Instructions ---
# DEFAULT_LOGO_INSTRUCTION = """You are a creative brand designer specialized in generating high-quality logos.

# Your task is to generate a professional, high-resolution logo based on the user's description and the reference images provided.

# Generate a graphic similar to the attachment

# - The top of the report should start with the Google Cloud logo on the white background followed by the Title "TRIP Report". 

# - Below that there is a placeholder [Insert Customer Logo]. Put the second image that is attached there. Also on the white background. Make this image smaller than the total space it takes for the Google Cloud and Trip Report Header
# - Below that create the blue box that fills the width of the standard 8.5 x 11 page. The contents of the box should be a timeline image similar to the first attachment. 
#     - it should have the date of the event and below it a bubble with the course title, instructor name and number of attendees. Replace the circular image for each instructor with the corresponding image found in the JSON data provided below. The instructor image should not appear twice or above the date bubble, only once per class inside the blue bubble below the date and timeline bar.
#     - They should be sorted by earliest to latest date. 

# User prompt will contain filenames or descriptions. Ensure the final logo is consistent with the ROITraining brand (if applicable).
# """

DEFAULT_LOGO_INSTRUCTION = """You are a professional info-graphic designer. 
- first call the tool "process_gcs_manifest_tool" with the user prompt which contains formatted JSON data to get the GCS paths for the template, company logo, and instructor photos.
- I want you to generate an info-graphic similar to the attachment called template.
- LAYOUT RULES:  
  * WHITE HEADER (top of page):  
  * Left side: Google Cloud logo (cloud icon only, no text) + "TRIP Report" in black, font-size 20px on the same line Below that (with extra line spacing): 
  * Company logo at 1/3 the height and width of the header row above it, left-aligned 
  * DARK RED BOX (fills remaining page width, background #0D2B63 or similar dark navy) and found by using the attachment called company_logo 
  * Top-left heading: "Completed PLLJ Training Overview" in white, bold 
  * Below heading: Company name provided from the tool in bright blue (#4DA6FF or similar), bold, larger font 
- Below the header you will generate a timeline according to the following rules:
  * Horizontal line across the box with one entry per course, sorted earliest to latest. 
  * Each entry has: 
    1. A blue pill/bubble/box ABOVE the timeline line with the formatted date (e.g. "Jan 1, 2026")   
    2. A vertical connector line to the timeline.
    3. A rounded blue card BELOW the timeline containing:
      - Course title (top) 
      - Instructor photo found by matching the name of the instructor to the images fetched from the process_gcs_manifest_tool
      - The instructor name next to that with the first name above the last name on two lines
    4. at the bottom of the pill/bubble/box show the icon and the number of attendees
  * The horizontal line begins with a vertical connector line and ends with a vertical connector line. There must be as many vertical lines as there are dates and bubbles. And the first and last should be at the beginning and end of the line.  
  BOTTOM-LEFT of blue box: ROI Training logo (globe icon + "ROI Training" in white) 
  * Do NOT include the company logo inside the blue box 
Overall the generated graphic should look similar in it's overall layout to the provided template but with the correct number of events based on the data that is supply in the prompt
There should be no more than 5 pill/bubble/boxes across, so if there are more than five events, format it to use multiple lines and balance the number of boxes for events across to be roughly even. 
 - for examples 5 events two rows with 3 & 2, 6 events two rows with 3 & 3, 7 events three rows with 3 & 2 & 2, 8 events three rows with 3 & 3 & 2, 9 events three rows with 3 & 3 & 3, 10 events four rows with 3 & 3 & 2 & 2
"""
# — show ONCE per card, inside the card only     - Attendee count as a number only (no label), with a group-people icon next to it  - Do NOT show instructor name text, do NOT show "Attendees:" label, do NOT show instructor photo above the date or outside the card 
 

# Fetch latest instructions for 'sight_logo' from Firestore
# instructions = get_latest_instruction("trip_report_logo_generator") or DEFAULT_LOGO_INSTRUCTION
instructions = DEFAULT_LOGO_INSTRUCTION

# --- Define the Agent ---
sight_logo = Agent(
    name="sight_logo"
    # Using Gemini 3.1 Flash Image Preview for generation
    , model=os.getenv("LOGO_MODEL", "gemini-3.1-flash-image-preview")
    , instruction = instructions
    , tools=[process_gcs_manifest_tool_images]
    , before_model_callback=log_query_to_model
    , after_model_callback=log_model_response
    , before_tool_callback=before_tool_callback
    , after_tool_callback=after_tool_callback
)

root_agent = sight_logo

if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner, types
    
    async def main():
        runner = InMemoryRunner(agent=sight_logo)
        session_id = "test_session"
        user_id = "test_user"
        
        # Ensure session exists
        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
        if not session:
            await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=user_id,
                session_id=session_id
            )

        print(f"Testing sight_logo agent with prompt: 'ABC'...")
        prompt = """
        Use the tool: process_gcs_manifest_tool to process the following data into the right format and then generate the sight_logo. Pass the following data exactly as is into the function tool call:
        {"company":"Rackspace", "template":"TRIP_Template.png", "classes": [{"date": "2026-01-01", "instructor":"Joey Gagliardo", "title":"App Dev with LLM", "attendees":15}, {"date": "2026-02-01", "instructor":"Joey Gagliardo", "title": "Google ADK", "attendees":20}, {"date":"2026-03-01", "instructor":"Doug Rehnstrom", "title":"Gemini for Workspace", "attendees":9}]}
        """
        new_message = types.Content(parts=[types.Part(text=prompt)])
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent Response: {part.text}")
                    if part.inline_data:
                        print(f"🎨 Infographic generated! Saving to infographic.png...")
                        # part.inline_data.data contains the raw bytes or base64
                        image_data = part.inline_data.data
                        
                        # If it's a string, it's base64 encoded
                        if isinstance(image_data, str):
                            import base64
                            image_bytes = base64.b64decode(image_data)
                        else:
                            image_bytes = image_data

                        with open("infographic.png", "wb") as f:
                            f.write(image_bytes)
                        print("✅ Saved to infographic.png")
    
    asyncio.run(main())
