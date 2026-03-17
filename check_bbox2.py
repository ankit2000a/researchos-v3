import json
import glob
import sys
import os
import traceback

files = glob.glob("/Users/akshay/Build/ResearchOS_Core/backend/backend/logs/audit_trail_*.json")
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

found = False
for f_path in files:
    with open(f_path, 'r') as f:
        try:
            content = f.read()
            # The file might contain multiple JSON objects, one per line (JSONL) 
            # or a JSON array. In the file we viewed, it was a JSON array like [ { ... } , ... ]
            try:
                data_list = json.loads(content)
                if not isinstance(data_list, list):
                    # Maybe it's not a list
                    data_list = [data_list]
            except Exception:
                # Fallback to json lines
                data_list = [json.loads(line) for line in content.strip().split('\n') if line.strip()]

            for data in data_list:
                coords = data.get('coordinates')
                if coords:
                    if coords[0] != 400.0 and coords[0] != 100.0 and coords[0] != 50.0:
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

if not found:
    print("NO REAL COORDINATES FOUND")
