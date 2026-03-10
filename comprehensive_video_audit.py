import json
import os
import glob

JOB_PATH = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436"
JSON_PATH = os.path.join(JOB_PATH, "presentation.json")
VIDEO_PATH = os.path.join(JOB_PATH, "videos")
OUTPUT_PATH = r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\video_audit_report.txt"

def comprehensive_audit():
    if not os.path.exists(JSON_PATH):
        print("ERROR: presentation.json not found")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get all physical video files
    video_files = set()
    if os.path.exists(VIDEO_PATH):
        video_files = set(os.listdir(VIDEO_PATH))
    
    sections = data.get("sections", [])
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write("=" * 100 + "\n")
        out.write("JOB 48808436 COMPREHENSIVE VIDEO AUDIT\n")
        out.write("=" * 100 + "\n\n")
        
        out.write(f"Total Physical Video Files in /videos/: {len(video_files)}\n\n")
        
        # Header
        out.write(f"{'SEC':<4} {'TYPE':<10} {'RENDERER':<8} {'SEGS':<6} {'PROMPTS':<8} {'EXPECTED':<10} {'DOWNLOADED':<12} {'STATUS'}\n")
        out.write("-" * 100 + "\n")
        
        total_segments = 0
        total_prompts = 0
        total_expected = 0
        total_downloaded = 0
        
        for sec in sections:
            sid = sec.get("section_id")
            stype = sec.get("section_type")
            renderer = sec.get("renderer")
            
            # Count segments
            num_segments = len(sec.get("narration", {}).get("segments", []))
            total_segments += num_segments
            
            # Count prompts (from video_prompts array)
            prompts = sec.get("video_prompts", [])
            num_prompts = len(prompts)
            total_prompts += num_prompts
            
            # Expected videos: count unique beat_ids or manim output
            expected_videos = set()
            if renderer == "manim":
                expected_videos.add(f"topic_{sid}.mp4")
            elif renderer == "video":
                for p in prompts:
                    beat_id = p.get("beat_id")
                    if beat_id:
                        expected_videos.add(f"{beat_id}.mp4")
            
            num_expected = len(expected_videos)
            total_expected += num_expected
            
            # Count actually downloaded
            downloaded = []
            for v in expected_videos:
                if v in video_files:
                    downloaded.append(v)
            num_downloaded = len(downloaded)
            total_downloaded += num_downloaded
            
            # Status
            if renderer in ["video", "manim"]:
                if num_downloaded == num_expected and num_expected > 0:
                    status = "✅ COMPLETE"
                elif num_downloaded > 0:
                    status = f"⚠️ PARTIAL ({num_expected - num_downloaded} missing)"
                elif num_expected > 0:
                    status = "❌ NONE"
                else:
                    status = "N/A"
            else:
                status = "N/A (No Video)"
            
            out.write(f"{sid:<4} {stype:<10} {renderer:<8} {num_segments:<6} {num_prompts:<8} {num_expected:<10} {num_downloaded:<12} {status}\n")
        
        out.write("-" * 100 + "\n")
        out.write(f"{'TOTAL':<4} {'':<10} {'':<8} {total_segments:<6} {total_prompts:<8} {total_expected:<10} {total_downloaded:<12}\n")
        out.write("\n")
        
        # Explain the odd/even pattern
        out.write("=" * 100 + "\n")
        out.write("EXPLANATION: ODD/EVEN SEGMENT PATTERN\n")
        out.write("=" * 100 + "\n")
        out.write("""
Per V2.5 Director Bible, Content sections follow a "Teach -> Show" pattern:
  - Segment 1 (Odd): "Teach" - Avatar explains. Visual = Text/Diagram. NO VIDEO NEEDED.
  - Segment 2 (Even): "Show" - Video demonstrates. Visual = Full Video. VIDEO PROMPT REQUIRED.
  - Segment 3 (Odd): "Teach" - Avatar explains next point. NO VIDEO NEEDED.
  - Segment 4 (Even): "Show" - Video demonstrates. VIDEO PROMPT REQUIRED.
  ... and so on.

The LLM generates "Cinematic educational visualization" (a placeholder) for "Teach" segments
because per the Bible, the visual layer should be HIDDEN during "Teach" (avatar only).
However, the current code still generates a WAN prompt for ALL segments, leading to
placeholder prompts for odd segments.

CONCLUSION: This is a DESIGN ISSUE in the pipeline, not a generation failure.
"Teach" segments should NOT generate WAN videos at all. They should use static visuals (text/diagram).
""")
        
        out.write("\n")
        out.write("=" * 100 + "\n")
        out.write("PHYSICAL VIDEO FILES LIST (First 20)\n")
        out.write("=" * 100 + "\n")
        for i, v in enumerate(sorted(video_files)[:20]):
            out.write(f"  {v}\n")
        if len(video_files) > 20:
            out.write(f"  ... and {len(video_files) - 20} more\n")
    
    print(f"Report written to: {OUTPUT_PATH}")

if __name__ == "__main__":
    comprehensive_audit()
