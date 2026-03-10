import json
from pathlib import Path

# Job Configuration
JOB_ID = "603bd693"
SECTION_ID = 3

# Paths
job_dir = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs") / JOB_ID
pres_path = job_dir / "presentation.json"

if not pres_path.exists():
    print(f"Error: presentation.json not found at {pres_path}")
    exit(1)

with open(pres_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Patch Section 3
sections = data.get("sections", [])
patched_count = 0

for sec in sections:
    # Identify Manim sections (Section 3 and 5)
    s_id = sec.get("section_id") or sec.get("id")
    
    # Patch both Section 3 and 5 (or any Manim section)
    if sec.get("renderer") == "manim":
        print(f"Patching Section {s_id} (Renderer: {sec.get('renderer')})")
        
        # Ensure renderer is manim
        if sec.get("renderer") != "manim":
            print(f"Warning: Renderer is {sec.get('renderer')}, expected 'manim'. Patching anyway.")
            
        segments = sec.get("narration", {}).get("segments", [])
        for i, seg in enumerate(segments):
            # Apply force-show visual directives
            seg["display_directives"] = {
                "text_layer": "hide",
                "visual_layer": "show",
                "avatar_layer": "show" 
            }
            patched_count += 1
            print(f"  Segment {i}: Set visual_layer='show', text_layer='hide'")

if patched_count > 0:
    with open(pres_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\nSUCCESS: Patched {patched_count} segments in presentation.json")
else:
    print(f"\nWARNING: No segments found to patch for Section {SECTION_ID}")
