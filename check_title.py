import json
import glob
import sys
import os

files = glob.glob("/Users/akshay/Build/ResearchOS_Core/backend/logs/audit_trail_*.json")
if not files:
    # try backend/backend/logs
    files = glob.glob("/Users/akshay/Build/ResearchOS_Core/backend/backend/logs/audit_trail_*.json")

files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

found = False
for f_path in files[:5]:
    with open(f_path, 'r') as f:
        try:
            content = f.read()
            data_list = []
            try:
                data_list = json.loads(content)
                if not isinstance(data_list, list):
                    data_list = [data_list]
            except:
                data_list = [json.loads(line) for line in content.strip().split('\n') if line.strip()]

            for data in data_list:
                if data.get('data_field') in ['study_title', 'title', 'Study Title']:
                    print(f"File: {f_path}")
                    print(f"Field: {data.get('data_field')}")
                    print(f"Extracted: {repr(data.get('extracted_value'))}")
                    print(f"Reasoning: {data.get('agent_reasoning')}")
                    print(f"Coordinates: {data.get('coordinates')}")
                    found = True
        except Exception as e:
            pass
if not found:
    print("No title found in recent logs")
