import sys
import os
import json
from dotenv import load_dotenv

sys.path.append("/Users/akshay/Build/ResearchOS_Core/backend")
load_dotenv("/Users/akshay/Build/ResearchOS_Core/backend/.env")

from core.vision_specialist import VisionSpecialist
v = VisionSpecialist()
print(f"Key loaded: {bool(v.api_key)}")

# Find a pdf
pdfs = [f for f in os.listdir("/Users/akshay/Build/ResearchOS_Core/backend/uploads") if f.endswith(".pdf")]
if pdfs:
    pdf_path = os.path.join("/Users/akshay/Build/ResearchOS_Core/backend/uploads", pdfs[0])
    print(f"Testing with {pdf_path}")
    
    hash_val = v._upload_pdf(pdf_path)
    print(f"Uploaded, hash: {hash_val}")
    res = v._get_result(hash_val, max_wait=300)
    
    with open("whisperer_dump.json", "w") as f:
        json.dump(res, f, indent=2)
    print("Saved to whisperer_dump.json")
    
    for i in range(min(5, len(res.get('vision_map', [])))):
        print(f"Map Item {i}: {res['vision_map'][i]}")
else:
    print("No PDFs found to test.")
