"""
Utility script to clear truncated manim_code from presentation.json.
This forces the pipeline to regenerate using V25 prompts.

Usage: python clear_truncated_manim.py <job_id>
"""
import json
import sys
import os
from pathlib import Path

def clear_truncated_manim(job_id: str):
    """Clear manim_code fields that appear truncated so they can be regenerated."""
    
    jobs_dir = Path("player/jobs") / job_id
    pres_path = jobs_dir / "presentation.json"
    
    if not pres_path.exists():
        print(f"ERROR: {pres_path} not found!")
        return False
    
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    cleared_count = 0
    
    for section in presentation.get("sections", []):
        manim_code = section.get("manim_code", "")
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        
        if renderer == "manim" and manim_code:
            # Check for truncation patterns
            lines = manim_code.strip().split("\n")
            last_line = lines[-1].strip() if lines else ""
            
            is_truncated = False
            truncation_reason = ""
            
            # Common truncation patterns
            if last_line.endswith("="):
                is_truncated = True
                truncation_reason = "ends with '='"
            elif last_line.endswith("("):
                is_truncated = True
                truncation_reason = "ends with '('"
            elif last_line.endswith(","):
                is_truncated = True
                truncation_reason = "ends with ','"
            elif "= MathTex" in last_line and ")" not in last_line:
                is_truncated = True
                truncation_reason = "incomplete MathTex"
            elif "= Text" in last_line and ")" not in last_line:
                is_truncated = True
                truncation_reason = "incomplete Text"
            
            if is_truncated:
                print(f"  Section {section_id}: TRUNCATED ({truncation_reason})")
                print(f"    Last line: {last_line[:60]}...")
                print(f"    Clearing manim_code to force regeneration...")
                section["manim_code"] = None
                cleared_count += 1
            else:
                print(f"  Section {section_id}: OK (complete)")
    
    if cleared_count > 0:
        # Backup original
        backup_path = jobs_dir / "presentation.json.bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2)
        print(f"\n  Backup saved to: {backup_path}")
        
        # Save updated
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2)
        print(f"  Updated presentation.json: Cleared {cleared_count} truncated section(s)")
        print(f"\n✅ Now retry the Manim phase from Dashboard to regenerate with V25 prompts!")
    else:
        print("\n✅ No truncated manim_code found. All sections look complete.")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clear_truncated_manim.py <job_id>")
        print("Example: python clear_truncated_manim.py d5cc9830")
        sys.exit(1)
    
    job_id = sys.argv[1]
    print(f"\n=== Checking Job {job_id} for Truncated Manim Code ===\n")
    clear_truncated_manim(job_id)
