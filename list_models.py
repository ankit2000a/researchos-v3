import os
import sys
from dotenv import load_dotenv

sys.path.append("/Users/akshay/Build/ResearchOS_Core/backend")
load_dotenv("/Users/akshay/Build/ResearchOS_Core/backend/.env")

from google import genai

client = genai.Client()
for m in client.models.list():
    if 'gemini' in m.name and ('3' in m.name or '1.5' in m.name):
        print(f"Model: {m.name}")
