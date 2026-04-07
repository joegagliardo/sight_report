import re

def convert_gcs_to_https(text):
    gs_pattern = r'gs://([a-zA-Z0-9\._\-]+)/([a-zA-Z0-9\._\-/]+)'
    
    # Simulate the logic in EnhancedCourseSearchTool
    gs_match = re.search(gs_pattern, text)
    if gs_match:
        bucket = gs_match.group(1)
        path = gs_match.group(2)
        return f"https://storage.googleapis.com/{bucket}/{path}"
    return None

# Test cases
test_cases = [
    "gs://roitraining-dashboard-grounding/gcp/C-AGTSPI-B_DS_EN.pdf",
    "Some text with gs://my-bucket/path/to/file.txt in it",
    "https://cloud.google.com/training", # Should return None
    "gs://bucket-name/file_name.pdf"
]

print("Verifying GCS to HTTPS conversion logic:")
for case in test_cases:
    result = convert_gcs_to_https(case)
    print(f"Input: {case}")
    print(f"Output: {result}")
    print("-" * 20)

# Verify pattern matching for typical GCS paths
sample_content = '{"gcs_uri": "gs://roitraining-dashboard-grounding/gcp/C-AGTSPI-B_DS_EN.pdf", "title": "Course Title"}'
converted = convert_gcs_to_https(sample_content)
print(f"Sample Content Match: {converted}")
if converted == "https://storage.googleapis.com/roitraining-dashboard-grounding/gcp/C-AGTSPI-B_DS_EN.pdf":
    print("SUCCESS: Conversion logic is correct.")
else:
    print("FAILURE: Conversion logic did not match expected output.")
