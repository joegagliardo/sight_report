import os
import asyncio
from flask import Flask, render_template, request, Response, stream_with_context, send_from_directory
from flask_cors import CORS

# --- Environment Detection for GCP/Cloud Run ---
if os.environ.get("K_SERVICE"):
    # Force use of Vertex AI backend instead of Gemini API when on Cloud Run.
    # This prevents the "No API key was provided" error.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

from sight_report.agent import sight_agent
from sight_logo.agent import sight_logo
from google.adk.runners import InMemoryRunner, types
from google.adk.events import Event
import firestore_utils

app = Flask(__name__)
CORS(app)

# --- Admin Routes ---
@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/api/prompts", methods=["GET"])
def get_prompts():
    prompts = firestore_utils.get_all_prompts()
    return {"prompts": prompts}

@app.route("/api/prompts", methods=["POST"])
def post_prompt():
    data = request.json
    agent_name = data.get("agent_name")
    instructions = data.get("instructions")
    if not (agent_name and instructions):
        return {"error": "Missing agent_name or instructions"}, 400
    
    success = firestore_utils.add_prompt(agent_name, instructions)
    if success:
        return {"success": True}
    else:
        return {"error": "Failed to save to Firestore"}, 500

# Initialize runners for different agents
runners = {
    "sight_reader": InMemoryRunner(agent=sight_agent),
    "sight_logo": InMemoryRunner(agent=sight_logo)
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory('reports', filename)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("prompt")
    session_id = request.json.get("sessionId", "default_session")
    agent_name = request.json.get("agent_name", "sight_reader")
    
    if not user_input:
        return {"error": "No prompt provided"}, 400

    runner = runners.get(agent_name, runners["sight_reader"])

    # --- Image Injection Logic for sight_logo ---
    parts = [types.Part(text=user_input)]
    if agent_name == "sight_logo":
        import re
        # 1. Look for full gs:// paths
        gs_pattern = r'gs://[a-zA-Z0-9\._\-]+/[\w\.\-\/]+\.(?:png|jpg|jpeg|webp)'
        found_gs_uris = re.findall(gs_pattern, user_input)
        
        # 2. Look for simple filenames (fallback)
        filename_pattern = r'\b[\w\-]+\.(?:png|jpg|jpeg|webp)\b'
        all_matches = re.finditer(filename_pattern, user_input)
        
        # Use a set to avoid duplicates and track what's already handled by gs://
        processed_uris = set()
        
        # Handle full URIs first
        for uri in found_gs_uris:
            if uri not in processed_uris:
                ext = uri.split('.')[-1].lower()
                mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                print(f"💉 Injecting GS URI: {uri} ({mime_type})")
                parts.append(types.Part(
                    file_data=types.FileData(mime_type=mime_type, file_uri=uri)
                ))
                processed_uris.add(uri)
        
        # Handle simple filenames that weren't part of a gs:// path
        bucket = os.getenv("LOGO_BUCKET", "roitraining-dashboard.appspot.com")
        for match in all_matches:
            filename = match.group(0)
            # Check if this filename is part of a gs:// path already found
            is_in_gs = any(filename in uri for uri in found_gs_uris)
            
            if not is_in_gs:
                file_uri = f"gs://{bucket}/{filename}"
                if file_uri not in processed_uris:
                    ext = filename.split('.')[-1].lower()
                    mime_type = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                    print(f"💉 Injecting fallback filename: {file_uri} ({mime_type})")
                    parts.append(types.Part(
                        file_data=types.FileData(mime_type=mime_type, file_uri=file_uri)
                    ))
                    processed_uris.add(file_uri)

    # Build the message content using ADK/GenAI types
    new_message = types.Content(parts=parts)

    def generate():
        # Set up a new loop for this request
        new_loop = asyncio.new_event_loop()
        
        async def run_agent():
            try:
                # 1. Ensure the session exists
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

                # 2. Universal Extractor (recursive)
                def extract_content(obj):
                    """Yields strings for text and data URLs for images."""
                    if obj is None:
                        return
                        
                    if isinstance(obj, str):
                        yield obj
                    elif isinstance(obj, dict):
                        # 1. Direct text field
                        text = obj.get("text")
                        if isinstance(text, str) and text.strip():
                            yield text
                        
                        # 2. Part-like structure (text or inline_data)
                        if "inline_data" in obj:
                            data = obj["inline_data"].get("data")
                            mime = obj["inline_data"].get("mime_type")
                            if data and mime:
                                yield f"MEDIA:data:{mime};base64,{data}"
                        
                        # 3. Recurse into all dictionary values
                        for k, v in obj.items():
                            # Skip recurse into 'text' if we already handled it
                            if k == "text": continue
                            yield from extract_content(v)
                            
                    elif isinstance(obj, list):
                        for item in obj:
                            yield from extract_content(item)
                    
                    # Handle ADK/GenAI internal objects via duck typing
                    elif hasattr(obj, "parts"): # Content objects
                        for part in obj.parts:
                            yield from extract_content(part)
                    elif hasattr(obj, "text") and obj.text: # Part objects
                        yield obj.text
                    elif hasattr(obj, "inline_data") and obj.inline_data: # Image Part
                        data = getattr(obj.inline_data, 'data', None)
                        mime = getattr(obj.inline_data, 'mime_type', None)
                        if data and mime:
                            yield f"MEDIA:data:{mime};base64,{data}"
                    elif hasattr(obj, "to_dict"):
                        yield from extract_content(obj.to_dict())

                # 3. Stream Events
                async for event in runner.run_async(
                    user_id="default_user",
                    session_id=session_id,
                    new_message=new_message
                ):
                    # Pulse heartbeat to keep connection alive and visible
                    yield "data: [PULSE]\n\n"

                    # Extract content using the recursive crawler
                    has_found_content = False
                    
                    # Filter: Do not stream raw data from the BigQuery agent
                    if event.content and getattr(event, 'agent_id', None) != "bq_agent":
                        for chunk in extract_content(event.content):
                            if chunk:
                                if chunk.startswith("MEDIA:"):
                                    # Send media tag
                                    yield f"data: {chunk}\n\n"
                                else:
                                    # Standard text
                                    for line in chunk.split('\n'):
                                        yield f"data: {line}\n"
                                    yield "\n" # End of chunk
                                has_found_content = True
                    
                    # LOGGING for deep diagnostics
                    if event.content and not has_found_content:
                         print(f"--- FAILED TO EXTRACT CONTENT FROM EVENT {event.id} ---")
                    else:
                         print(f"[STREAM] Event ID: {getattr(event, 'id', 'N/A')} (Found: {has_found_content})")

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: Error during stream: {str(e)}\n\n"

        # 4. Bridge to synchronous Flask
        gen = run_agent()
        while True:
            try:
                chunk = new_loop.run_until_complete(gen.__anext__())
                yield chunk
            except StopAsyncIteration:
                break
            except Exception as e:
                yield f"data: Error in generator: {str(e)}\n\n"
                break
        
        new_loop.close()

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Cache-Control'] = 'no-cache'
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
