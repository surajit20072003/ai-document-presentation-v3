
import json
import datetime
from pathlib import Path

# Path to jobs index
jobs_file = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\jobs_index.json")

try:
    if jobs_file.exists():
        with open(jobs_file, 'r') as f:
            jobs = json.load(f)
            
        count = 0
        for job_id, job in jobs.items():
            if job.get("status") == "processing":
                job["status"] = "failed"
                job["error"] = "Manually reset: Job stuck or cancelled by user"
                job["failed_at"] = datetime.datetime.now().isoformat()
                count += 1
                print(f"Updated job {job_id} to FAILED.")
                
        if count > 0:
            with open(jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2, default=str)
            print(f"Successfully reset {count} processing jobs.")
        else:
            print("No processing jobs found.")
    else:
        print("jobs_index.json not found.")
except Exception as e:
    print(f"Error updating jobs: {e}")
