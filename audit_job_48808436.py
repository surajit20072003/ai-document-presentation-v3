
import json
import os
import glob

JOB_PATH = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436"
JSON_PATH = os.path.join(JOB_PATH, "presentation.json")
VIDEO_PATH = os.path.join(JOB_PATH, "videos")

def audit_job():
    if not os.path.exists(JSON_PATH):
        print("ERROR: presentation.json not found")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    print(f"Total Sections: {len(sections)}")
    
    video_files = set(os.listdir(VIDEO_PATH)) if os.path.exists(VIDEO_PATH) else set()
    print(f"Total Video Files Found: {len(video_files)}")

    missing_prompts = []
    missing_videos = []
    section_status = []

    for sec in sections:
        sid = sec.get("section_id")
        stype = sec.get("section_type")
        renderer = sec.get("renderer")
        title = sec.get("title", "No Title")
        
        status = {
            "id": sid,
            "type": stype,
            "renderer": renderer,
            "has_prompts": False,
            "expected_videos": [],
            "found_videos": [],
            "missing_videos": []
        }

        # Check for prompts
        if renderer == "video" or stype == "recap": # WAN/Recap usually need prompts
             # Check render_spec
             render_spec = sec.get("render_spec", {})
             segment_specs = render_spec.get("segment_specs", [])
             
             # Also check video_prompts
             video_prompts = sec.get("video_prompts", [])
             
             prompts_found = 0
             if segment_specs:
                 for spec in segment_specs:
                     if spec.get("video_prompt"):
                         prompts_found += 1
             
             if video_prompts:
                  prompts_found += len(video_prompts)

             if prompts_found > 0:
                 status["has_prompts"] = True
             else:
                 # Manim might not use render_spec in the same way, or uses code.
                 # But user asked about prompts.
                 # Manim prompts are in render_prompts.json usually.
                 pass

        # Check for expected videos based on beat_videos or output_path
        # Usually defined in narration -> segments -> beat_videos
        narration = sec.get("narration", {})
        segments = narration.get("segments", [])
        
        for seg in segments:
            beat_videos = seg.get("beat_videos", [])
            for bv in beat_videos:
                status["expected_videos"].append(bv + ".mp4") # Assuming mp4
                
        # Check existence
        for v in status["expected_videos"]:
            # Check if file exists (case insensitive?)
            if v in video_files:
                status["found_videos"].append(v)
            else:
                status["missing_videos"].append(v)
                missing_videos.append(f"Section {sid}: {v}")
        
        # Check Manim specific (usually topic_{sid}.mp4)
        if renderer in ["manim", "manim_v15"]:
             manim_file = f"topic_{sid}.mp4"
             status["expected_videos"].append(manim_file)
             if manim_file in video_files:
                 status["found_videos"].append(manim_file)
             else:
                 status["missing_videos"].append(manim_file)
                 missing_videos.append(f"Section {sid} (Manim): {manim_file}")

        section_status.append(status)

    # Report
    print("\n--- SECTION AUDIT ---")
    for s in section_status:
        # Determine prompt status
        prompt_msg = "Prompts: OK" if s["has_prompts"] else "Prompts: NONE"
        if s["renderer"] not in ["video", "manim_v15"] and s["type"] != "recap":
            prompt_msg = "Prompts: N/A"
        
        # Determine video status
        vid_count = len(s["expected_videos"])
        found_count = len(s["found_videos"])
        vid_msg = f"Videos: {found_count}/{vid_count}"
        
        print(f"Sec {s['id']} [{s['type']}/{s['renderer']}]: {prompt_msg}, {vid_msg}")
        if s["missing_videos"]:
            print(f"  Missing: {s['missing_videos'][:3]}...")

    print("\n--- SUMMARY ---")
    print(f"Missing Videos Count: {len(missing_videos)}")
    
    # Check Manim Prompts in render_prompts.json
    try:
        with open(os.path.join(JOB_PATH, "render_prompts.json"), "r") as f:
            rprompts = json.load(f)
            print(f"Manim Prompts found in render_prompts.json: {len(rprompts)}")
            manim_sections = [p["section_id"] for p in rprompts]
            print(f"Manim Sections: {manim_sections}")
    except:
        print("render_prompts.json not found or invalid")

if __name__ == "__main__":
    audit_job()
