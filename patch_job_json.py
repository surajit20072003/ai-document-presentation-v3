"""
Patch presentation.json to auto-upgrade sections with hidden content.
Fixes Job 4ee21a06 where LLM generated content but forgot to set renderer flag.
"""
import json
import sys
from pathlib import Path

JOB_ID = "4ee21a06"
job_dir = Path(f"player/jobs/{JOB_ID}")
pres_file = job_dir / "presentation.json"

if not pres_file.exists():
    print(f"❌ File not found: {pres_file}")
    sys.exit(1)

print(f"Reading {pres_file}...")
with open(pres_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

sections = data.get("sections", [])
changes = 0

print("\nScanning sections for hidden V2.5 content...")
for i, section in enumerate(sections):
    renderer = section.get("visual", {}).get("renderer", "none")
    # Also check legacy top-level renderer
    top_renderer = section.get("renderer", "none")
    
    # Check V2.5 render_spec location
    spec = section.get("render_spec") or {}
    has_manim = bool(spec.get("manim_scene_spec"))
    has_wan = bool(spec.get("video_prompts"))
    
    # Auto-upgrade if renderer is none but content exists
    if (renderer == "none" or top_renderer == "none") and (has_manim or has_wan):
        old_r = renderer if renderer != "none" else top_renderer
        
        if has_wan:
            new_r = "wan_video"
            if "visual" not in section: section["visual"] = {}
            section["visual"]["renderer"] = new_r
            section["renderer"] = new_r  # Synced
            print(f"  [S{i+1}] Upgraded to WAN_VIDEO (found {len(spec.get('video_prompts'))} prompts)")
            changes += 1
            
        elif has_manim:
            new_r = "manim_flow"
            if "visual" not in section: section["visual"] = {}
            section["visual"]["renderer"] = new_r
            section["renderer"] = new_r  # Synced
            print(f"  [S{i+1}] Upgraded to MANIM_FLOW (found Manim spec)")
            changes += 1

if changes > 0:
    # Update job status so retry works smoothly
    data["metadata"]["job_status"] = "in_progress"
    
    # Save back
    with open(pres_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Fixed {changes} sections! Saved to {pres_file}")
    print("Run video generation now.")
else:
    print("\nNo sections needed patching.")
