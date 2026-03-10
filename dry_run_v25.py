import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from core.pipeline_unified import process_markdown_unified

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DryRun")

def run_dry_run():
    load_dotenv()
    
    job_id = "v25_dry_run_testing"
    input_file = "test_input_v25.md"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        markdown = f.read()

    print(f"\n🚀 Starting dry run for job: {job_id}")
    print("-" * 40)

    try:
        presentation, tracker = process_markdown_unified(
            markdown_content=markdown,
            subject="Physics",
            grade="Grade 10",
            job_id=job_id,
            dry_run=True,
            pipeline_version="v15_v2_director",
            model="anthropic/claude-3-5-sonnet:beta" # Use a high fidelity model for prompt validation
        )

        print("\n✅ Dry run completed successfully!")
        print("-" * 40)
        
        # Verify debug files
        output_dir = Path(f"jobs/{job_id}")
        expected_files = [
            "presentation.json",
            "llm_debug_dump.json",
            "debug_global_worker.json"
        ]
        
        print("\n📂 Checking Job Directory:")
        for file in expected_files:
            p = output_dir / file
            if p.exists():
                print(f"  [FOUND] {file} ({p.stat().st_size} bytes)")
            else:
                print(f"  [MISSING] {file}")

        # Verify Recap Narration
        sections = presentation.get("sections", [])
        recap = next((s for s in sections if s.get("section_type") == "recap"), None)
        if recap:
            print("\n📺 Recap Narration Analysis:")
            segments = recap.get("narration", {}).get("segments", [])
            for i, seg in enumerate(segments):
                text = seg.get("text", "")
                words = len(text.split())
                print(f"  Segment {i+1}: {words} words")
        else:
            print("\n❌ Recap section not found in presentation.json")

    except Exception as e:
        logger.exception(f"Dry run failed: {e}")

if __name__ == "__main__":
    run_dry_run()
