import json
import re
from typing import Any, Optional
from google.adk.tools import DiscoveryEngineSearchTool

class EnhancedCourseSearchTool(DiscoveryEngineSearchTool):
    """
    Search tool that post-processes results to convert 'gs://' links 
    to public 'https://storage.googleapis.com/...' links.
    """
    
    def discovery_engine_search(self, query: str) -> dict[str, Any]:
        """
        Overrides the standard search to ensure hyperlinks point to GCS public storage.
        """
        # 1. Get raw results from the base tool
        response = super().discovery_engine_search(query)
        
        if response.get('status') != 'success':
            return response
            
        # 2. Process results
        results = response.get('results', [])
        for res in results:
            content = res.get('content', '')
            url = res.get('url', '')
            
            # Look for gs:// paths in both the url field and the content/metadata
            # Pattern matches gs://[bucket]/[path]
            gs_pattern = r'gs://([a-zA-Z0-9\._\-]+)/([a-zA-Z0-9\._\-/]+)'
            
            # Search in content (which often contains raw JSON for structured data)
            gs_match = re.search(gs_pattern, content)
            if not gs_match:
                # Search in the url field if content didn't have it
                gs_match = re.search(gs_pattern, url)
                
            if gs_match:
                bucket = gs_match.group(1)
                path = gs_match.group(2)
                https_url = f"https://storage.googleapis.com/{bucket}/{path}"
                
                # Prioritize this specific document link over any generic link
                res['url'] = https_url
                
                # Explicitly inject the URL into the content so the LLM identifies it easily
                res['content'] = f"--- SOURCE_DOCUMENT_LINK: {https_url} ---\n{content}"
            else:
                # If no gs:// link is found, but the URL is generic, 
                # we leave it as is, but the agent instructions will handle skipping if needed.
                pass
                
        return response
