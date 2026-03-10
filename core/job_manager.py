import os
import sys
import json
import uuid
import random
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Callable, List

JOBS_DIR = Path("player/jobs")
JOBS_INDEX_FILE = JOBS_DIR / "jobs_index.json"
STATUS_MESSAGES_FILE = Path(__file__).parent / "status_messages.json"

_status_messages_cache = None


def load_status_messages() -> dict:
    """Load status messages from JSON file (cached)."""
    global _status_messages_cache
    if _status_messages_cache is None:
        try:
            with open(STATUS_MESSAGES_FILE, 'r') as f:
                _status_messages_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _status_messages_cache = {"phases": {}}
    return _status_messages_cache


def get_phase_message(phase_key: str, is_failure: bool = False) -> str:
    """Get a random message for a phase, or failure message if is_failure=True."""
    messages = load_status_messages()
    phases = messages.get("phases", {})
    
    phase_key_normalized = phase_key.lower().replace(" ", "_")
    for key in [phase_key_normalized, phase_key]:
        if key in phases:
            phase = phases[key]
            if is_failure and "failure_message" in phase:
                return phase["failure_message"]
            if "messages" in phase and phase["messages"]:
                return random.choice(phase["messages"])
    
    return phase_key


def get_phase_display_name(phase_key: str) -> str:
    """Get the display name for a phase."""
    messages = load_status_messages()
    phases = messages.get("phases", {})
    
    phase_key_normalized = phase_key.lower().replace(" ", "_")
    for key in [phase_key_normalized, phase_key]:
        if key in phases:
            return phases[key].get("display_name", phase_key)
    
    return phase_key


def log(msg: str):
    """Print with immediate flush for real-time logging."""
    print(msg)
    sys.stdout.flush()


def load_jobs_index() -> Dict[str, dict]:
    """Load jobs index from disk."""
    if JOBS_INDEX_FILE.exists():
        try:
            with open(JOBS_INDEX_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_jobs_index(jobs: Dict[str, dict]):
    """Save jobs index to disk."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(JOBS_INDEX_FILE, 'w') as f:
            json.dump(jobs, f, indent=2, default=str)
    except IOError as e:
        log(f"[WARN] Failed to save jobs index: {e}")


from concurrent.futures import ThreadPoolExecutor

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, dict] = load_jobs_index()
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)  # Allow 2 parallel jobs (reduced from 4 for stability)
        self._startup_cleanup()
    
    def _startup_cleanup(self):
        """
        On startup, fail any jobs that were left in processing/pending/running/queued state.
        Also cleans up stuck avatar statuses.
        """
        changed = False
        interrupted_count = 0
        
        # 1. Pipeline Jobs Cleanup (Smart Recovery)
        with self._lock:
            for job_id, job in self._jobs.items():
                if job.get("status") in ["processing", "running", "queued", "pending"]:
                    job_dir = JOBS_DIR / job_id
                    pres_path = job_dir / "presentation.json"
                    
                    if pres_path.exists():
                        log(f"[STARTUP] Found interrupted job {job_id} with saved presentation. Enabling Smart Recovery.")
                        job["status"] = "completed_with_errors"
                        job["error"] = None # Clear error to show "Completed with Errors" in UI
                        job["status_message"] = "Interrupted during asset generation. Partial results saved."
                        job["failure_message"] = "Server restart interrupted asset generation. You can now retry specific assets."
                    else:
                        log(f"[STARTUP] Found stuck job {job_id} (no saved state). Auto-failing.")
                        job["status"] = "failed"
                        job["error"] = "System Restarted - Job Interrupted. Please Retry."
                        job["failure_message"] = "The server was restarted while this job was running."
                    
                    job["completed_at"] = datetime.now().isoformat()
                    interrupted_count += 1
                    changed = True
        
        if changed:
            self._persist()
            log(f"[STARTUP] Cleaned up {interrupted_count} stale pipeline jobs.")

        # 2. Avatar Status Cleanup (Local file based)
        try:
            cleaned_avatars = 0
            if JOBS_DIR.exists():
                for job_folder in JOBS_DIR.iterdir():
                    if job_folder.is_dir():
                        status_file = job_folder / "avatar_status.json"
                        if status_file.exists():
                            try:
                                data = json.loads(status_file.read_text())
                                if data.get("state") == "processing":
                                    data["state"] = "failed"
                                    data["error"] = "Avatar generation was interrupted due to server restart."
                                    status_file.write_text(json.dumps(data, indent=2))
                                    cleaned_avatars += 1
                            except Exception:
                                pass
            if cleaned_avatars > 0:
                log(f"[STARTUP] Cleaned up {cleaned_avatars} stuck avatar tasks.")
        except Exception as e:
            log(f"[STARTUP] Avatar cleanup failed: {e}")
    
    def _persist(self):
        """Save current jobs state to disk."""
        with self._lock:
            save_jobs_index(self._jobs)
    
    def create_job(self, job_type: str, params: dict, prefix: str = None) -> str:
        # Generate ID with optional prefix
        base_uuid = str(uuid.uuid4())[:8]
        if prefix:
            # Sanitize prefix (alphanumeric + underscore only)
            clean_prefix = "".join(c if c.isalnum() else "_" for c in prefix)
            # Truncate to reasonable length (e.g. 32 chars) to avoid filesystem issues
            clean_prefix = clean_prefix[:32]
            # Ensure no trailing/leading underscores
            clean_prefix = clean_prefix.strip("_")
            if clean_prefix:
                job_id = f"{clean_prefix}_{base_uuid}"
            else:
                job_id = base_uuid
        else:
            job_id = base_uuid
        
        queued_message = get_phase_message("queued")
        
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "params": params,
                "status": "queued",
                "current_step": None,
                "current_step_name": "Waiting in Queue",
                "current_phase_key": "queued",
                "status_message": queued_message,
                "steps_completed": 0,
                "total_steps": 4 if job_type == "pdf" else 3,
                "progress": 0,
                "blueprint_ready": False,  # NEW: Initialize to false, set to true when presentation.json saved
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "error": None,
                "result": None
            }
        
        self._persist()
        return job_id
    
    def get_job(self, job_id: str) -> Optional[dict]:
        with self._lock:
            return self._jobs.get(job_id, None)
    
    def get_all_jobs(self) -> List[dict]:
        """Get all jobs, sorted by created_at descending."""
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return jobs
    
    def update_job(self, job_id: str, updates: dict, persist: bool = False):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)
        if persist:
            self._persist()
    
    def set_step(self, job_id: str, step_name: str, step_number: int, phase_key: str = None):
        job = self.get_job(job_id)
        if job:
            total = job.get("total_steps", 4)
            progress = int((step_number / total) * 100)
            
            display_name = step_name
            status_message = None
            if phase_key:
                display_name = get_phase_display_name(phase_key)
                status_message = get_phase_message(phase_key)
            
            self.update_job(job_id, {
                "current_step": step_number,
                "current_step_name": display_name,
                "current_phase_key": phase_key or step_name.lower().replace(" ", "_"),
                "status_message": status_message,
                "progress": progress
            }, persist=True)
    
    def complete_step(self, job_id: str, step_number: int):
        job = self.get_job(job_id)
        if job:
            total = job.get("total_steps", 4)
            progress = int(((step_number + 1) / total) * 100)
            self.update_job(job_id, {
                "steps_completed": step_number + 1,
                "progress": min(progress, 99)
            }, persist=True)
    
    def complete_job(self, job_id: str, result: dict = None, status: str = "completed"):
        completed_message = get_phase_message(status)
        updates = {
            "status": status,
            "progress": 100,
            "current_step_name": "Complete!",
            "current_phase_key": "completed",
            "status_message": completed_message,
            "completed_at": datetime.now().isoformat()
        }
        if result is not None:
            updates["result"] = result
            
        self.update_job(job_id, updates, persist=True)
    
    def fail_job(self, job_id: str, error: str, phase_key: str = None):
        job = self.get_job(job_id)
        effective_phase = phase_key or (job.get("current_phase_key") if job else None)
        
        failure_message = None
        impact = None
        dev_hint = None
        
        if effective_phase:
            messages = load_status_messages()
            phases = messages.get("phases", {})
            phase_key_normalized = effective_phase.lower().replace(" ", "_")
            for key in [phase_key_normalized, effective_phase]:
                if key in phases:
                    phase_data = phases[key]
                    if "failure_message" in phase_data:
                        failure_message = phase_data["failure_message"]
                    if "impact" in phase_data:
                        impact = phase_data["impact"]
                    if "dev_hint" in phase_data:
                        dev_hint = phase_data["dev_hint"]
                    break
        
        self.update_job(job_id, {
            "status": "failed",
            "error": error,
            "failure_message": failure_message,
            "impact": impact,
            "dev_hint": dev_hint,
            "failed_phase": effective_phase,
            "completed_at": datetime.now().isoformat()
        }, persist=True)
    
    def start_job(self, job_id: str):
        self.update_job(job_id, {
            "status": "processing",
            "started_at": datetime.now().isoformat()
        }, persist=True)

    def submit_task(self, func: Callable, *args, **kwargs):
        """Submit an arbitrary task to the thread pool (respecting max_workers)."""
        return self._executor.submit(func, *args, **kwargs)




job_manager = JobManager()


def run_job_async(job_id: str, process_func: Callable, **kwargs):
    def worker():
        log(f"[JOB {job_id}] Worker thread started...")
        try:
            log(f"\n[JOB {job_id}] Starting job...")
            job_manager.start_job(job_id)
            result = process_func(job_id=job_id, **kwargs)
            log(f"[JOB {job_id}] Job completed successfully!")
            
            # Determine final status from result metadata if available
            # Determine final status from result metadata if available
            final_status = "completed"
            pending_tasks = False
            
            if isinstance(result, dict):
                 meta_status = result.get("metadata", {}).get("job_status")
                 if meta_status == "completed_with_errors":
                     final_status = "completed_with_errors"
                 if result.get("pending_background_tasks"):
                     pending_tasks = True
                     
            elif isinstance(result, tuple) and len(result) > 0 and isinstance(result[0], dict):
                 # Handle (presentation, tracker) tuple
                 meta_status = result[0].get("metadata", {}).get("job_status")
                 if meta_status == "completed_with_errors":
                     final_status = "completed_with_errors"
                 if result[0].get("pending_background_tasks"):
                     pending_tasks = True

            if not pending_tasks:
                job_manager.complete_job(job_id, result, status=final_status)
            else:
                log(f"[JOB {job_id}] Kept in processing state (pending background tasks)")
                # STATUS UPDATE: Mark as LLM Complete, explicitly requested by user
                job_manager.update_job(job_id, {
                    "status": "processing",
                    "current_step_name": "LLM Completed_Processing_Assets",
                    "current_phase_key": "assets_pending"
                }, persist=True)
                
                # Persist partial result so frontend has output paths
                if result:
                    job_manager.update_job(job_id, {"result": result}, persist=True)
        except Exception as e:
            import traceback
            full_traceback = traceback.format_exc()
            log(f"\n[JOB {job_id}] JOB FAILED!")
            log(f"[JOB {job_id}] Error: {str(e)}")
            log(f"[JOB {job_id}] Traceback:\n{full_traceback}")
            
            # ISS-204: Capture full traceback for debugging
            error_with_trace = f"{str(e)}\n\nTraceback:\n{full_traceback}"
            job_manager.fail_job(job_id, error_with_trace)
            
            # ISS-204: Also update analytics.json with the error
            try:
                job = job_manager.get_job(job_id)
                if job and job.get("output_dir"):
                    from pathlib import Path
                    import json
                    analytics_path = Path(job["output_dir"]) / "analytics.json"
                    analytics = {}
                    if analytics_path.exists():
                        with open(analytics_path, 'r') as f:
                            analytics = json.load(f)
                    analytics["status"] = "failed"
                    analytics["error"] = str(e)
                    analytics["traceback"] = full_traceback
                    analytics["failed_at"] = datetime.now().isoformat()
                    with open(analytics_path, 'w') as f:
                        json.dump(analytics, f, indent=2)
                    log(f"[JOB {job_id}] Error persisted to analytics.json")
            except Exception as analytics_error:
                log(f"[JOB {job_id}] Failed to update analytics: {analytics_error}")
    
    log(f"[JOB {job_id}] Submitting job to thread pool...")
    job_manager._executor.submit(worker)
    return None


def is_job_running() -> bool:
    """Check if any job is currently processing."""
    jobs = job_manager.get_all_jobs()
    return any(j.get("status") == "processing" for j in jobs)


def get_current_job_ids() -> List[str]:
    """Get IDs of all currently processing jobs."""
    jobs = job_manager.get_all_jobs()
    return [j["id"] for j in jobs if j.get("status") == "processing"]
