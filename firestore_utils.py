import os
import datetime
from google.cloud import firestore

def get_latest_instruction(agent_name: str) -> str:
    """
    Fetches the latest instruction for a given agent from the Firestore 
    database 'sight-report' in the 'prompts' collection.
    
    Args:
        agent_name: The name of the agent (e.g., 'sight_report_analyst').
    
    Returns:
        The instruction string, or None if not found.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "roitraining-dashboard")
    database_id = "sight-report"
    
    try:
        # Initialize Firestore client with the specific named database
        db = firestore.Client(project=project_id, database=database_id)
        
        # Query the prompts collection
        prompts_ref = db.collection("prompts")
        query = prompts_ref.where("agent_name", "==", agent_name).order_by(
            "date_entered", direction=firestore.Query.DESCENDING
        ).limit(1)
        
        results = list(query.stream())
        
        if not results:
            print(f"⚠️ No instructions found in Firestore for agent: {agent_name}")
            return None
            
        return results[0].to_dict().get("instructions")
        
    except Exception as e:
        print(f"❌ Error fetching from Firestore: {str(e)}")
        return None

def get_all_prompts():
    """
    Fetches all instructions from the 'prompts' collection, ordered by 
    date_entered (descending).
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "roitraining-dashboard")
    database_id = "sight-report"
    
    try:
        db = firestore.Client(project=project_id, database=database_id)
        prompts_ref = db.collection("prompts")
        query = prompts_ref.order_by("date_entered", direction=firestore.Query.DESCENDING)
        
        results = list(query.stream())
        return [r.to_dict() for r in results]
    except Exception as e:
        print(f"❌ Error fetching all prompts: {str(e)}")
        return []

def add_prompt(agent_name: str, instructions: str):
    """
    Adds a new prompt definition to the 'prompts' collection.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "roitraining-dashboard")
    database_id = "sight-report"
    
    try:
        db = firestore.Client(project=project_id, database=database_id)
        data = {
            "agent_name": agent_name,
            "instructions": instructions,
            "date_entered": datetime.datetime.now(datetime.timezone.utc)
        }
        db.collection("prompts").add(data)
        return True
    except Exception as e:
        print(f"❌ Error adding prompt: {str(e)}")
        return False
