import sys
import os
sys.path.append("/Users/akshay/Build/ResearchOS_Core/backend")

from core.vision_specialist import VisionSpecialist

v = VisionSpecialist()
v.api_key = "mock" # avoid real api

mock_data = {
    "line_metadata": [
        [1, 100, 10, 1000],  # page 1, bottom y 100, height 10, page height 1000
    ],
    "result_text": "Sample line of text\n"
}

vision_map = v._create_vision_map_from_response(mock_data)

print("Vision Map Result:")
for item in vision_map:
    print(item)
