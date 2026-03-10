"""
Manim + Avatar Only - Skip TTS

This script:
1. Renders Manim videos from existing code files
2. Submits Avatar generation jobs
3. Completely skips TTS (you can add audio later)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.agents.avatar_generator import AvatarGenerator

JOB_ID = "d76a0cc1"
JOBS_DIR = Path("player/jobs")
JOB_DIR = JOBS_DIR / JOB_ID

def run_manim_and_avatar():
    print(f"=" * 80)
    print(f"MANIM + AVATAR GENERATION FOR JOB {JOB_ID}")
    print(f"=" * 80)
    print("\nSkipping TTS - will process Manim rendering and Avatar generation only\n")
    
    # Load presentation
    pres_path = JOB_DIR / "presentation.json"
    with open(pres_path, "r", encoding="utf-8") as f:
        presentation = json.load(f)
    
    sections = presentation.get("sections", [])
    print(f"Loaded presentation with {len(sections)} sections")
    
    # Step 1: Render Manim Videos
    print(f"\n{'='*80}")
    print("STEP 1: Rendering Manim Videos")
    print(f"{'='*80}\n")
    
    manim_code_dir = JOB_DIR / "manim_code"
    videos_dir = JOB_DIR / "videos"
    videos_dir.mkdir(exist_ok=True)
    
    if not manim_code_dir.exists():
        print("⚠️  No manim_code directory found - skipping Manim rendering")
        print("   Run retry_job_generation.py first to generate Manim code")
    else:
        code_files = list(manim_code_dir.glob("section_*.py"))
        print(f"Found {len(code_files)} Manim code files")
        
        if code_files:
            print("\nRendering Manim videos...")
            print("NOTE: This may take several minutes depending on complexity\n")
            
            import subprocess
            rendered = 0
            failed = 0
            
            for code_file in code_files:
                section_num = code_file.stem.replace("section_", "")
                output_file = videos_dir / f"section_{section_num}.mp4"
                
                # Check if already exists
                if output_file.exists() and output_file.stat().st_size > 10000:
                    print(f"✓ Section {section_num}: Already rendered ({output_file.stat().st_size:,} bytes)")
                    rendered += 1
                    continue
                
                print(f"→ Section {section_num}: Rendering...", end=" ", flush=True)
                
                try:
                    # Render with Manim
                    cmd = [
                        "manim",
                        "-ql",  # Low quality for speed
                        "--disable_caching",
                        str(code_file),
                        "MainScene",
                        "-o", f"section_{section_num}.mp4"
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=str(JOB_DIR)
                    )
                    
                    # Manim puts output in media/videos/{filename}/480p15/
                    manim_output = JOB_DIR / "media" / "videos" / code_file.stem / "480p15" / f"section_{section_num}.mp4"
                    
                    if manim_output.exists():
                        # Move to videos directory
                        import shutil
                        shutil.move(str(manim_output), str(output_file))
                        print(f"✅ Done ({output_file.stat().st_size:,} bytes)")
                        rendered += 1
                    else:
                        print(f"❌ Failed (output not found)")
                        failed += 1
                        
                except subprocess.TimeoutExpired:
                    print(f"❌ Timeout")
                    failed += 1
                except Exception as e:
                    print(f"❌ Error: {e}")
                    failed += 1
            
            print(f"\nManim Summary: {rendered} rendered, {failed} failed")
            
            # Cleanup media directory
            media_dir = JOB_DIR / "media"
            if media_dir.exists():
                import shutil
                shutil.rmtree(media_dir, ignore_errors=True)
        else:
            print("No Manim code files to render")
    
    # Step 2: Submit Avatar Generation
    print(f"\n{'='*80}")
    print("STEP 2: Submitting Avatar Generation")
    print(f"{'='*80}\n")
    
    try:
        avatar_gen = AvatarGenerator()
        results = avatar_gen.submit_parallel_job(presentation, JOB_ID, str(JOB_DIR))
        
        print(f"✅ Avatar submission complete:")
        print(f"   - Queued: {len(results['queued'])}")
        print(f"   - Skipped: {len(results['skipped'])} (already exist)")
        print(f"   - Failed: {len(results['failed'])}")
        
        if results['queued']:
            print(f"\n📝 Avatar videos will generate in background")
            print(f"   Check: player/jobs/{JOB_ID}/avatar_status.json")
            
    except Exception as e:
        print(f"❌ Avatar submission failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("COMPLETE - MANIM + AVATAR")
    print(f"{'='*80}")
    print("\n📋 Status:")
    print(f"   ✅ Manim videos: player/jobs/{JOB_ID}/videos/")
    print(f"   ⏳ Avatar videos: Generating in background")
    print(f"   ⚠️  TTS audio: Skipped (add later if needed)")
    print(f"\nYou can view the presentation now - it will have:")
    print(f"   - Manim animations ✅")
    print(f"   - Avatar videos (when ready) ⏳")
    print(f"   - No narration audio ⚠️")

if __name__ == "__main__":
    run_manim_and_avatar()
