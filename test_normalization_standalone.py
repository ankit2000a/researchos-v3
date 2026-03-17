import json
import re

title = "TALOs, Fill the Gap: Tafasitamab and Lenalidomide in Diffuse Large B-Cell Lymphoma in the Real-Life Patient Journey"
clean_value = str(title).strip().lower().replace(',', '').replace(' ', '')
print(f"Clean value: {clean_value}")

with open('whisperer_dump.json', 'r') as f:
    data = json.load(f)

vmap = data.get('vision_map', [])
found = False

for elem in vmap:
    elem_text = elem.get('value', elem.get('text', ''))
    if not elem_text: continue
    
    clean_elem = str(elem_text).strip().lower().replace(',', '').replace(' ', '')
    
    if clean_value == clean_elem or clean_value in clean_elem or clean_elem in clean_value:
        print(f"MATCHED: {elem_text}")
        found = True
        break
    
    # Just in case, let's see if partial matches work:
    if "talo" in clean_elem:
        print(f"Partial look at 'talo' line: '{elem_text}' -> '{clean_elem}'")

if not found:
    print("NO MATCH FOUND")
