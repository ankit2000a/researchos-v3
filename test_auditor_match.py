import sys
sys.path.append('/Users/akshay/Build/ResearchOS_Core/backend')

from core.auditor import Auditor

auditor = Auditor("test")
extracted_val = "TALOs, Fill the Gap: Tafasitamab and Lenalidomide in Diffuse Large B-Cell Lymphoma in the Real-Life Patient Journey"

# Make mock vision map
vision_map = [
    {
        "id": "line_3",
        "value": "TALOs, Fill the Gap: Tafasitamab and Lenalidomide in",
        "coords": [0, 10, 100, 5],
        "page": 1
    }
]

from unittest.mock import patch
coords, bbox_id, page = auditor._verify_geometry(extracted_val, vision_map)
print(f"Match result: {coords}, {bbox_id}, {page}")
