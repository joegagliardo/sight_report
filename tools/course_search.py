import json
import re
from typing import Any, Optional, List, Dict
from google.adk.tools import DiscoveryEngineSearchTool
from vertexai.generative_models import Part, Image

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
        bucket_name = "roitraining-dashboard-grounding"
        
        for res in results:
            content = res.get('content', '')
            url = res.get('url', '')
            https_url = None
            
            # --- Method 1: Look for explicit gs:// paths ---
            gs_pattern = r'gs://([a-zA-Z0-9\._\-]+)/([a-zA-Z0-9\._\-/]+\.[a-zA-Z0-9]+)'
            gs_match = re.search(gs_pattern, content) or re.search(gs_pattern, url)
            
            if gs_match:
                bucket = gs_match.group(1)
                path = gs_match.group(2)
                https_url = f"https://storage.googleapis.com/{bucket}/{path}"
                print(f"DEBUG: Transform GCS Path {gs_match.group(0)} -> {https_url}")
            
            # --- Method 2: Look for Course Reference Codes (e.g., Ref: T-AK8S-I-2.0) ---
            if not https_url:
                ref_pattern = r'Ref:\s*([A-Z0-9\-]+)'
                ref_match = re.search(ref_pattern, content)
                if ref_match:
                    code = ref_match.group(1)
                    # Mapping logic: Strip version suffix if it exists and append _DS_EN.pdf
                    # E.g., T-AK8S-I-2.0 -> T-AK8S-I_DS_EN.pdf
                    # We'll try to find a clean code (up to the last dash or if it's already short)
                    clean_code = code
                    if '-' in code:
                        parts = code.split('-')
                        # If last part looks like a version (has . or is digit), strip it
                        if '.' in parts[-1] or parts[-1].isdigit():
                            clean_code = "-".join(parts[:-1])
                    
                    https_url = f"https://storage.googleapis.com/{bucket_name}/gcp/{clean_code}_DS_EN.pdf"
                    # print(f"DEBUG: Synthesized URL from {code} -> {https_url}")

            if https_url:
                res['url'] = https_url
                res['content'] = f"--- SOURCE_DOCUMENT_LINK: {https_url} ---\n{content}"
            else:
                # Fallback: if it's already a public storage link, keep it
                pass
                
        return response
                
        return response

