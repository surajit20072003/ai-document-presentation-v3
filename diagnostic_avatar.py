import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AvatarDiagnostic")

# Load env
load_dotenv(override=True)

# Add core to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.agents.avatar_generator import AvatarGenerator
except ImportError:
    print("Error: Could not import AvatarGenerator. Make sure you run this from the project root.")
    sys.exit(1)

def run_diagnostic():
    print("="*50)
    print("AVATAR GENERATION DIAGNOSTIC")
    print("="*50)

    api_url = os.environ.get("AVATAR_API_URL")
    print(f"API URL: {api_url}")
    if not api_url:
        print("ERROR: AVATAR_API_URL not found in .env")
        return

    generator = AvatarGenerator()
    
    # Test Payload
    test_text = "This is a diagnostic test for avatar generation and saving."
    job_id = "diagnostic_test"
    section_id = 999
    
    print(f"\n[1] Submitting test job...")
    print(f"    Text: '{test_text}'")
    
    try:
        response = generator.generate_avatar_video(test_text, job_id, section_id)
        print(f"    Response: {response}")
    except Exception as e:
        print(f"    ERROR submitting job: {e}")
        return

    if "task_id" not in response:
        print("    ERROR: No task_id returned.")
        return

    task_id = response["task_id"]
    print(f"\n[2] Task ID received: {task_id}")
    
    # Poll
    print(f"\n[3] Polling for completion...")
    start_time = time.time()
    while time.time() - start_time < 300: # 5 mins timeout
        status_res = generator.check_status(task_id)
        status = status_res.get("status")
        print(f"    Status: {status}")
        
        if status == "completed" or (status_res.get("result", {}).get("success") is True):
            print("\n[4] Task Completed!")
            
            # Check Output URL
            output_url = status_res.get("output_url")
            print(f"    Output URL from API: {output_url}")
            
            # Try Download
            output_dir = Path("diagnostic_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"avatar_{task_id}.mp4"
            print(f"\n[5] Attempting download to: {output_path}")
            
            try:
                success = generator.download_video(task_id, str(output_path))
                if success:
                    print(f"    SUCCESS: Video saved to {output_path}")
                    print(f"    File size: {output_path.stat().st_size} bytes")
                else:
                    print("    FAILURE: Download returned False")
            except Exception as e:
                print(f"    ERROR during download: {e}")
            
            break
            
        elif status in ["failed", "error"]:
            print(f"    FAILURE: Task failed on server. Reason: {status_res}")
            break
            
        time.sleep(5)

if __name__ == "__main__":
    run_diagnostic()
