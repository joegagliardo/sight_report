import os
from dotenv import load_dotenv
from google.adk.tools import DiscoveryEngineSearchTool

load_dotenv()

def test_search():
    data_store_id = "projects/roitraining-dashboard/locations/global/collections/default_collection/dataStores/gcp-course-outlines"
    location = "global"
    
    search_tool = DiscoveryEngineSearchTool(data_store_id=data_store_id, location=location)
    
    query = "GKE security Anthos service mesh course outlines"
    print(f"Searching for: {query}\n")
    
    try:
        # Assuming the tool is callable
        results = search_tool(query=query)
        print("Results:")
        print(results)
    except Exception as e:
        print(f"Error test searching: {e}")

if __name__ == "__main__":
    test_search()
