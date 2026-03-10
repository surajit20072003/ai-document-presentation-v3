import json
from pathlib import Path

def audit_narrations(job_id):
    pres_path = Path(f"player/jobs/{job_id}/presentation.json")
    if not pres_path.exists():
        print(f"Error: {pres_path} not found")
        return
        
    with open(pres_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    sections = data.get("sections", [])
    print(f"REPORT FOR JOB {job_id}")
    print(f"==============================")
    print(f"Total Sections: {len(sections)}")
    
    total_chars = 0
    for s in sections:
        sid = s.get("section_id")
        text = s.get("narration", {}).get("full_text", "")
        chars = len(text)
        total_chars += chars
        print(f"Section {sid:2}: {chars:5} chars | Title: {s.get('title')}")
        
    print(f"==============================")
    print(f"Total Narration Chars: {total_chars}")
    print(f"Source Doc Chars (Metadata): {data.get('metadata', {}).get('doc_length')}")

if __name__ == "__main__":
    audit_narrations("d76a0cc1")
