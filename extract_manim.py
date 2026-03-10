import json
from pathlib import Path

def extract_manim_code(json_file, section_id):
    for encoding in ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']:
        try:
            with open(json_file, 'r', encoding=encoding) as f:
                data = json.load(f)
            print(f"Loaded with {encoding}")
            break
        except Exception as e:
            continue
    else:
        print("Failed to decode JSON with standard encodings.")
        return None
    
    for section in data.get('sections', []):
        sid = section.get('section_id')
        print(f"Checking section {sid}")
        # Handle "section_5" vs 5 vs "5"
        str_sid = str(sid)
        target = str(section_id)
        if str_sid == target or str_sid == f"section_{target}" or target == str_sid.replace("section_", ""):
            print(f"Found target section {sid}")
            code = section.get('manim_code')
            if code:
                return code
            else:
                print(f"No manim_code found in section {sid}")
    return None

if __name__ == "__main__":
    json_path = 'local_presentation_fail.json'
    for encoding in ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']:
        try:
            with open(json_path, 'r', encoding=encoding) as f:
                data = json.load(f)
            print(f"Loaded with {encoding}")
            break
        except Exception as e:
            continue
    else:
        print("Failed to load JSON")
        exit(1)
    
    manim_sections = []
    for section in data.get('sections', []):
        if section.get('renderer') == 'manim':
            manim_sections.append(section.get('section_id'))
    
    print(f"Sections with Manim renderer: {manim_sections}")
    
    code = None
    matched_sid = None
    for sid in manim_sections:
        for section in data.get('sections', []):
            if section.get('section_id') == sid:
                c = section.get('manim_code')
                if c:
                    code = c
                    matched_sid = sid
                    break
        if code:
            break
    
    if code:
        Path('tests').mkdir(exist_ok=True)
        with open('tests/test_manim_render_local.py', 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"Successfully extracted code from section {matched_sid} to tests/test_manim_render_local.py")
    else:
        print("No manim_code found in any Manim section!")
        # Fallback: look for manim_spec
        for sid in manim_sections:
            for section in data.get('sections', []):
                if section.get('section_id') == sid:
                    spec = section.get('manim_spec')
                    if spec:
                        print(f"Found manim_spec in section {sid}: {spec[:100]}...")
