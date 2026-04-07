import json
from typing import List, Dict, Any

def process_gcs_manifest_tool_test(input_json: str, base_bucket: str = "gs://roitraining-dashboard-grounding") -> Dict[str, str]:
    base_bucket = base_bucket.rstrip('/') + '/'
    data = json.loads(input_json)
    manifest = {}

    def get_full_uri(key: str, filename: str) -> str:
        if filename.startswith("gs://"):
            return filename
        k_low = key.lower()
        if k_low == "template":
            folder = "templates"
        elif k_low in ["company", "company_logo", "company_name"]:
            folder = "company/logos"
        else:
            folder = "instructor_photos"
        return f"{base_bucket}{folder}/{filename}"

    for key, value in data.items():
        if key.lower() == "classes" and isinstance(value, list):
            counter = 1
            for cls_obj in value:
                instructor = cls_obj.get("instructor")
                if instructor:
                    filename = f"{instructor}.png"
                    label = f"instructor_{counter}"
                    manifest[label] = get_full_uri(label, filename)
                    counter += 1
        else:
            if isinstance(value, str):
                manifest[key] = get_full_uri(key, value)

    return manifest

# Test cases
test_input = {
    "company": "Rackspace",
    "template": "TRIP_Template.png",
    "classes": [
        {"instructor": "Joey Gagliardo"},
        {"instructor": "Doug Rehnstrom"}
    ]
}

print("Running Refactored Path Logic Test...")
manifest = process_gcs_manifest_tool_test(json.dumps(test_input))

print(json.dumps(manifest, indent=2))

assert manifest["template"] == "gs://roitraining-dashboard-grounding/templates/TRIP_Template.png"
assert manifest["company"] == "gs://roitraining-dashboard-grounding/company/logos/Rackspace"
assert manifest["instructor_1"] == "gs://roitraining-dashboard-grounding/instructor_photos/Joey Gagliardo.png"
assert manifest["instructor_2"] == "gs://roitraining-dashboard-grounding/instructor_photos/Doug Rehnstrom.png"

print("\nAll tests passed! (No underscores in instructor filenames)")
