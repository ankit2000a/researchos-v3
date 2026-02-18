
def normalize(text):
    if not text:
        return ""
    return str(text).strip().lower().replace(',', '').replace(' ', '')

def verify_geometry(value_str, vision_map):
    if not vision_map or not value_str:
        return None
    
    clean_value = normalize(value_str)
    
    for elem in vision_map:
        if not elem: continue
        
        elem_text = elem.get('value', elem.get('text', ''))
        if not elem_text: continue
        
        clean_elem = normalize(elem_text)
        
        if clean_value == clean_elem or clean_value in clean_elem or clean_elem in clean_value:
            return elem.get('coords'), elem.get('text')
            
    return None

def test():
    # Case 1: Comma match
    map1 = [{"text": "43,548", "coords": [10, 10, 100, 20]}]
    val1 = "43548"
    res1, txt1 = verify_geometry(val1, map1)
    assert res1 == [10, 10, 100, 20], f"Failed Case 1: {res1}"
    print("✅ Case 1 Passed (Cross-format match)")

    # Case 2: Spaces
    map2 = [{"text": "p < 0.05", "coords": [5, 5, 50, 10]}]
    val2 = "p<0.05"
    res2, txt2 = verify_geometry(val2, map2)
    assert res2 == [5, 5, 50, 10], f"Failed Case 2: {res2}"
    print("✅ Case 2 Passed (Space normalization)")

if __name__ == "__main__":
    test()
