import os
import asyncio
from google.adk.runners import InMemoryRunner, types
from sight_logo.agent import sight_logo
from dotenv import load_dotenv

load_dotenv()

async def verify_agent():
    print("🚀 Verifying sight_logo agent...")
    
    # 1. Initialize Runner
    runner = InMemoryRunner(agent=sight_logo)
    
    # 2. Ensure session exists
    session_id = "test_session"
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id="default_user",
        session_id=session_id
    )
    if not session:
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="default_user",
            session_id=session_id
        )

    # 3. Mock user input with a filename and a full GS path
    user_input = "Create a minimalist version of Apple.png and gs://roitraining-dashboard.appspot.com/Rackspace.png"
    
    # 4. Image Injection (mimicking app.py)
    import re
    # 1. Look for full gs:// paths
    gs_pattern = r'gs://[a-zA-Z0-9\._\-]+/[\w\.\-\/]+\.(?:png|jpg|jpeg|webp)'
    found_gs_uris = re.findall(gs_pattern, user_input)
    
    # 2. Look for simple filenames (fallback)
    filename_pattern = r'\b[\w\-]+\.(?:png|jpg|jpeg|webp)\b'
    all_matches = re.finditer(filename_pattern, user_input)
    
    processed_uris = set()
    parts = [types.Part(text=user_input)]

    # Handle full URIs
    for uri in found_gs_uris:
        if uri not in processed_uris:
            ext = uri.split('.')[-1].lower()
            mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
            print(f"💉 Injecting GS URI: {uri}")
            parts.append(types.Part(
                file_data=types.FileData(mime_type=mime_type, file_uri=uri)
            ))
            processed_uris.add(uri)
    
    # Handle simple filenames
    bucket = os.getenv("LOGO_BUCKET", "roitraining-dashboard.appspot.com")
    for match in all_matches:
        filename = match.group(0)
        is_in_gs = any(filename in uri for uri in found_gs_uris)
        if not is_in_gs:
            file_uri = f"gs://{bucket}/{filename}"
            if file_uri not in processed_uris:
                ext = filename.split('.')[-1].lower()
                mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                print(f"💉 Injecting fallback URI: {file_uri}")
                parts.append(types.Part(
                    file_data=types.FileData(mime_type=mime_type, file_uri=file_uri)
                ))
                processed_uris.add(file_uri)
    
    new_message = types.Content(parts=parts)
    
    print(f"📡 Sending message with {len(parts)-1} image parts...")
    
    try:
        # 4. Run the agent
        async for event in runner.run_async(
            user_id="default_user",
            session_id=session_id,
            new_message=new_message
        ):
            if event.content:
                print(f"📦 Received Event Content: {event.id}")
                # Check for image parts in response
                for part in event.content.parts:
                    if part.text:
                        print(f"  [TEXT]: {part.text}")
                    if part.inline_data:
                        print(f"  [IMAGE]: Received base64 image ({part.inline_data.mime_type})")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(verify_agent())
