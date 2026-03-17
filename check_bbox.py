import json
import glob
import sys
import os

files = glob.glob("/Users/akshay/Build/ResearchOS_Core/backend/backend/logs/audit_trail_*.json")
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

found = False
for f_path in files:
    with open(f_path, 'r') as f:
        try:
            data_list = json.load(f)
            for data in data_list:
                coords = data.get('coordinates')
                if coords and coords[0] != 400.0 and coords[0] != 100.0 and coords[0] != 50.0:
                    print(f"File: {f_path}")
                    print(f"Field: {data.get('data_field')}")
                    print(f"Reasoning: {data.get('agent_reasoning')}")
                    print(f"Coordinates: {coords}")
                    found = True
                    break
        except Exception as e:
            pass
    if found:
        break
