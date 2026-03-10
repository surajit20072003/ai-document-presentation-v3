import json
from pathlib import Path
import re

# Paths
job_dir = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\603bd693")
source_path = job_dir / "source_markdown.md"
pres_path = job_dir / "presentation.json"

def clean_text(text):
    return re.sub(r'\s+', ' ', text).lower().strip()

print(f"--- GAP ANALYSIS FOR JOB 603bd693 ---")

# 1. READ SOURCE
if not source_path.exists():
    print("Source markdown not found!")
    exit(1)
with open(source_path, "r", encoding="utf-8") as f:
    source_content = f.read()
    
print(f"Source MD Length: {len(source_content)} chars")
print(f"Source MD Word Count: {len(source_content.split())} words")

# 2. READ PRESENTATION
if not pres_path.exists():
    print("Presentation JSON not found!")
    exit(1)
with open(pres_path, "r", encoding="utf-8") as f:
    pres_data = json.load(f)

print(f"Presentation Title: {pres_data.get('title')}")

# 3. EXTRACT PRESENTATION TEXT
pres_text = ""
sections = pres_data.get("sections", [])
section_details = []

for sec in sections:
    sec_title = sec.get("title", "Untitled")
    sec_type = sec.get("section_type")
    
    # Narrated text
    segments = sec.get("narration", {}).get("segments", [])
    sec_narration = " ".join([s.get("text", "") for s in segments])
    
    # Visual text
    sec_visual = ""
    for seg in segments:
        vc = seg.get("visual_content", {})
        if vc.get("verbatim_text"):
            sec_visual += " " + vc.get("verbatim_text")
        if vc.get("bullet_points"):
            bullets = vc.get("bullet_points")
            if isinstance(bullets, list):
                # Handle list of strings or dicts
                for b in bullets:
                    if isinstance(b, str): sec_visual += " " + b
                    elif isinstance(b, dict): sec_visual += " " + b.get("text", "")
    
    full_sec_text = sec_title + " " + sec_narration + " " + sec_visual
    pres_text += full_sec_text + " "
    
    section_details.append({
        "id": sec.get("section_id"),
        "title": sec_title,
        "type": sec_type,
        "narration_words": len(sec_narration.split()),
        "visual_words": len(sec_visual.split())
    })

print(f"Presentation Text Length: {len(pres_text)} chars")
print(f"Presentation Word Count: {len(pres_text.split())} words")

# 4. COMPARISON
ratio = len(pres_text.split()) / len(source_content.split())
print(f"Compression Ratio: {ratio:.2f}")

print("\n--- SECTION BREAKDOWN ---")
for s in section_details:
    print(f"Sec {s['id']} ({s['type']}): {s['title']} - {s['narration_words']} narrated words, {s['visual_words']} visual words")

# 5. KEYWORD CHECK (Mathematical terms for AP)
keywords = ["arithmetic progression", "common difference", "first term", "nth term", "sum", "sn", "an", "formula"]
print("\n--- KEYWORD CHECK ---")
for kw in keywords:
    in_source = kw in clean_text(source_content)
    in_pres = kw in clean_text(pres_text)
    status = "OK" if in_source == in_pres else ("MISSING" if in_source else "ADDED")
    print(f"'{kw}': {status} (Source: {in_source}, Pres: {in_pres})")
