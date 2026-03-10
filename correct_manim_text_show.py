import os
import json
import glob

def fix_job_manim_layers(job_dir):
    pres_path = os.path.join(job_dir, "presentation.json")
    if not os.path.exists(pres_path):
        return False
        
    try:
        with open(pres_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        sections = data.get("sections", [])
        changed = False
        
        for section in sections:
            # Look for Manim sections
            renderer = section.get("renderer", "")
            stype = section.get("section_type", "")
            
            if renderer in ["manim", "manim_flow"] and stype in ["content", "example"]:
                print(f"  Scanning Section: {section.get('title')} ({section.get('section_id')})")
                
                segments = section.get("narration", {}).get("segments", [])
                
                # Logic: Restore 'text_layer': 'show' for the FIRST segment (Teach Phase)
                # or any segment where visual_layer is NOT explicitly 'show' via directive
                
                for i, seg in enumerate(segments):
                    directives = seg.get("display_directives", {})
                    
                    # Assume Segment 0 is ALWAYS Teach phase
                    if i == 0:
                        if directives.get("text_layer") == "hide":
                            print(f"    FIXING Segment {i}: Resetting text_layer to 'show' (Teach Phase)")
                            directives["text_layer"] = "show"
                            directives["visual_layer"] = "hide" # Ensure video is hidden during teach
                            changed = True
                            
                    # For subsequent segments, check if they are explicitly Show Phase
                    # If they are NOT Show Phase, they might be Teach Phase 2
                    # But Manim usually has one long video... 
                    # Actually, V2.5 Director outputs explicit "text_layer": "show" for Teach segments.
                    # The bug was that ManimGenerator overwrote ALL of them to "hide".
                    # So simply verifying that if it shouldn't be hidden, we unhide it?
                    # Hard to know original intent without LLM re-run.
                    # SAFE FIX: Force Segment 0 to be Text Show.
                    
                    seg["display_directives"] = directives

        if changed:
            print(f"  [SAVING] applied fixes to {pres_path}")
            with open(pres_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        else:
            print(f"  [OK] No changes needed.")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Failed to process {pres_path}: {e}")
        return False

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    jobs_dir = os.path.join(root_dir, "player", "jobs")
    
    print(f"Scanning jobs in: {jobs_dir}")
    job_dirs = glob.glob(os.path.join(jobs_dir, "*"))
    
    count = 0
    fixed = 0
    
    for job in job_dirs:
        if os.path.isdir(job):
            print(f"Checking Job: {os.path.basename(job)}...")
            if fix_job_manim_layers(job):
                fixed += 1
            count += 1
            
    print(f"\nSummary: Scanned {count} jobs, Fixed {fixed} jobs.")

if __name__ == "__main__":
    main()
