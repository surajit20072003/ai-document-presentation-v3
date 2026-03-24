import os
import time
import requests
import logging
import json
from enum import Enum
from typing import Dict, Any, List, Optional
from core.latex_to_speech import latex_to_speech
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from core.analytics import AnalyticsTracker
from core.locks import presentation_lock, analytics_lock

logger = logging.getLogger(__name__)

class AvatarStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"

class AvatarGenerator:
    """
    Manages interaction with the Remote AI Avatar Generation API.
    """
    
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get("AVATAR_API_URL")
        if not self.api_url:
            raise ValueError("AVATAR_API_URL environment variable is not set")
        
    def generate_avatar_video(self, text: str, job_id: str, section_id: int, 
                             language: str = None, speaker: str = None) -> Dict[str, Any]:
        """
        Submit a request to generate an avatar video for the given text.
        
        Args:
            text (str): The raw narration text (can contain LaTeX).
            job_id (str): The job ID for context.
            section_id (int): The section ID for context.
            language (str, optional): Language code (e.g., "hindi", "tamil"). Default: None (English).
            speaker (str, optional): Voice ID (e.g., "vidya", "abhilash"). Only for Indian languages.
            
        Returns:
            Dict: Response containing 'task_id', 'status', etc.
        """
        # 1. Preprocess: Convert LaTeX using existing utility
        clean_text = latex_to_speech(text)
        lang_str = f" [{language}]" if language else ""
        logger.info(f"[AVATAR] Preprocessed text for Job {job_id}/Sec {section_id}{lang_str}: {clean_text[:50]}...")
        
        # 2. Submit to API
        try:
            url = f"{self.api_url}/generate"
            payload = {
                "text": clean_text
            }
            
            # Add optional language and speaker parameters
            if language:
                payload["language"] = language
                logger.info(f"[AVATAR] Language: {language}")
            
            if speaker:
                payload["speaker"] = speaker
                logger.info(f"[AVATAR] Speaker: {speaker}")
            
            # 2. Submit to API with Retry Logic
            max_retries = 3
            backoff_factor = 2
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"[AVATAR] Submitting to {url} (Attempt {attempt + 1}/{max_retries})")
                    response = requests.post(url, data=payload, timeout=60) # Increased timeout
                    
                    if response.status_code in [200, 202]:
                        data = response.json()
                        task_id = data.get("task_id")
                        print(f"[AVATAR-API] Success! Task ID: {task_id}", flush=True)
                        logger.info(f"[AVATAR] Task queued successfully: {task_id}")
                        return {
                            "task_id": task_id,
                            "status": "queued",
                            "clean_text": clean_text
                        }
                    elif response.status_code == 429: # Rate limit
                         wait = backoff_factor ** attempt
                         logger.warning(f"[AVATAR] Rate limited. Waiting {wait}s...")
                         time.sleep(wait)
                         continue
                    else:
                        logger.error(f"[AVATAR] API Error ({response.status_code}): {response.text}")
                        # Don't retry client errors (4xx) unless rate limit
                        if 400 <= response.status_code < 500:
                             return {"error": f"API Error: {response.text}", "status": "failed"}
                
                except requests.exceptions.RequestException as e:
                    logger.warning(f"[AVATAR] Network error on attempt {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(backoff_factor ** attempt)
                    else:
                        logger.error(f"[AVATAR] Max retries exceeded.")
                        return {"error": str(e), "status": "failed"}

            return {"error": "Max retries exceeded", "status": "failed"}
                
        except Exception as e:
            logger.error(f"[AVATAR] Request failed: {e}")
            return {"error": str(e), "status": "failed"}

    def check_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a specific avatar generation task.
        """
        try:
            url = f"{self.api_url}/status/{task_id}"
            print(f"[AVATAR-API] Checking status: {url}", flush=True)
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Support both nested (old) and flat (new) structures
                if "task_status" in data:
                    status = data["task_status"].get("status")
                    output_url = data["task_status"].get("output")
                else:
                    status = data.get("status")
                    # Construct output URL from result.data.result_url if available
                    result_block = data.get("result", {})
                    output_url = None
                    if isinstance(result_block, dict):
                        inner_data = result_block.get("data", {})
                        if isinstance(inner_data, dict):
                             rel_url = inner_data.get("result_url")
                             if rel_url:
                                 base = self.api_url.replace("/api", "")
                                 output_url = f"{base}{rel_url}"

                return {
                    "status": status,
                    "progress_chunks": [],
                    "output_url": output_url,
                    "raw_response": data
                }
            return {"status": "unknown", "error": f"Status check failed: {response.status_code}"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def download_video(self, task_id: str, output_path: str) -> bool:
        """
        Download the completed video. 
        Note: We need the full output URL which comes from check_status.
        If we don't have it, we try the legacy download endpoint or construct it.
        """
        try:
            # 1. Get Status to find the URL
            status_info = self.check_status(task_id)
            download_url = status_info.get("output_url")
            
            # Fallback to legacy endpoint if no URL found
            if not download_url:
                 download_url = f"{self.api_url}/download/{task_id}"
            
            logger.info(f"[AVATAR] Downloading from {download_url} to {output_path}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with requests.get(download_url, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        
            logger.info(f"[AVATAR] Download complete: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[AVATAR] Download failed: {e}")
            return False

    def _update_artifacts(self, output_dir: str, section_id: int, video_path: str, duration: float = 0.0, 
                         vimeo_url: Optional[str] = None, b2_url: Optional[str] = None,
                         language: str = None, speaker: str = None, task_id: str = None):
        """
        Live-patch presentation.json and analytics.json with the new avatar video and Vimeo info.
        This is crucial for "Fire-and-Forget" mode where the main pipeline has already exited.
        
        Args:
            language (str, optional): Language code for multi-language support.
            speaker (str, optional): Speaker ID for multi-language support.
            task_id (str, optional): Avatar API task ID for tracking.
        """
        try:
            out_path = Path(output_dir)
            pres_path = out_path / "presentation.json"
            
            # 1. Update Presentation.json
            if pres_path.exists():
                try:
                    with presentation_lock:
                        with open(pres_path, 'r', encoding='utf-8') as f:
                            pres_data = json.load(f)
                        
                        updated = False
                        for section in pres_data.get("sections", []):
                            if str(section.get("section_id")) == str(section_id):
                                # Player expects 'avatar_video' relative to job root (e.g. avatars/filename.mp4)
                                avatar_filename = os.path.basename(video_path)
                                
                                # Multi-language support: store in avatar_languages array
                                if language:
                                    # Ensure avatar_languages array exists
                                    if "avatar_languages" not in section:
                                        section["avatar_languages"] = []
                                    
                                    # Build language-specific path
                                    avatar_rel_path = f"avatars/{language}/{avatar_filename}"
                                    
                                    # Check if language entry exists, update or append
                                    lang_entry = None
                                    for entry in section["avatar_languages"]:
                                        if entry.get("language") == language:
                                            lang_entry = entry
                                            break
                                    
                                    if lang_entry:
                                        # Update existing entry
                                        lang_entry["video_path"] = avatar_rel_path
                                        lang_entry["status"] = "completed"
                                        lang_entry["duration"] = round(duration, 2)
                                    else:
                                        # Create new entry
                                        lang_entry = {
                                            "language": language,
                                            "video_path": avatar_rel_path,
                                            "status": "completed",
                                            "duration": round(duration, 2)
                                        }
                                        if speaker:
                                            lang_entry["speaker"] = speaker
                                        if task_id:
                                            lang_entry["task_id"] = task_id
                                        section["avatar_languages"].append(lang_entry)
                                    # VSYNC-001: store real MP4 duration at section level
                                    if duration > 0:
                                        section["avatar_duration_seconds"] = round(duration, 2)
                                    
                                    # Update URLs
                                    if vimeo_url:
                                        lang_entry["vimeo_url"] = vimeo_url
                                    if b2_url:
                                        lang_entry["b2_url"] = b2_url
                                    
                                    logger.info(f"[AVATAR] Updated avatar_languages for Sec {section_id} [{language}]")
                                else:
                                    # Default/English: use existing flat structure
                                    section["avatar_video"] = f"avatars/{avatar_filename}"
                                    section["avatar_status"] = "completed"
                                    # VSYNC-001: store real MP4 duration so player uses it as
                                    # totalDuration for Three.js — eliminates TTS-estimate drift
                                    if duration > 0:
                                        section["avatar_duration_seconds"] = round(duration, 2)
                                        logger.info(f"[AVATAR] VSYNC-001: stored real duration {duration:.2f}s for Sec {section_id}")
                                    
                                    # CRITICAL FIX: Store task_id for repair feature
                                    if task_id:
                                        section["avatar_task_id"] = task_id
                                        section["avatar_id"] = task_id
                                    
                                    # ISS-VIMEO: store vimeo details
                                    if vimeo_url:
                                        section["vimeo_url"] = vimeo_url
                                        section["vimeo_uploaded"] = True
                                        logger.info(f"[AVATAR] Added Vimeo URL for Sec {section_id}: {vimeo_url}")
                                    
                                    # B2: store backblaze details
                                    if b2_url:
                                        section["b2_url"] = b2_url
                                        section["b2_uploaded"] = True
                                        logger.info(f"[AVATAR] Added B2 URL for Sec {section_id}: {b2_url}")
                                
                                updated = True
                                break
                        
                        if updated:
                            with open(pres_path, 'w', encoding='utf-8') as f:
                                json.dump(pres_data, f, indent=2)
                            logger.info(f"[AVATAR] Updated presentation.json for Sec {section_id}")
                except Exception as e:
                    logger.error(f"[AVATAR] Failed to update presentation.json: {e}")

            # 2. Update Analytics.json (if exists)
            analytics_path = out_path / "analytics.json"
            if analytics_path.exists():
                try:
                    with analytics_lock:
                        with open(analytics_path, 'r', encoding='utf-8') as f:
                            analytics = json.load(f)
                        
                        # Update counts
                        if "avatar" not in analytics:
                            analytics["avatar"] = {"successful_sections": 0, "section_details": [], "failed_sections": 0, "total_sections": 0}
                        
                        avatar_metrics = analytics["avatar"]
                        avatar_metrics["successful_sections"] = avatar_metrics.get("successful_sections", 0) + 1
                        
                        # Add detail
                        detail = {
                            "section_id": section_id,
                            "duration_seconds": round(duration, 2),
                            "status": "completed",
                            "vimeo_url": vimeo_url,
                            "b2_url": b2_url,
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                        }
                        if "section_details" not in avatar_metrics:
                            avatar_metrics["section_details"] = []
                        avatar_metrics["section_details"].append(detail)
                        
                        with open(analytics_path, 'w', encoding='utf-8') as f:
                            json.dump(analytics, f, indent=2)
                        logger.info(f"[AVATAR] Updated analytics.json for Sec {section_id}")
                except Exception as e:
                    logger.error(f"[AVATAR] Failed to update analytics.json: {e}")

        except Exception as e:
            logger.error(f"[AVATAR] Critical error in _update_artifacts: {e}")

    def submit_parallel_job(self, presentation: Dict[str, Any], job_id: str, output_dir: str, 
                            tracker: Optional[AnalyticsTracker] = None,
                            languages: list = None, speaker: str = None) -> Dict[str, Any]:
        """
        Submits sections in strict batches of 3.
        For each batch:
          1. Submit concurrent requests.
          2. Wait for BOTH to complete (polling).
          3. Download videos.
          4. Only then proceed to next batch.
        
        This respects the 2-GPU limit by ensuring we never have more than 2 tasks active.
        
        Args:
            languages (list, optional): List of language codes. If None, generates English (default).
            speaker (str, optional): Voice ID for non-English languages.
        """
        logger.info(f"[AVATAR] Starting strict batch submission for Job {job_id}")
        sections = presentation.get("sections", [])
        total_sections = len(sections)
        
        # Default to English if no languages specified
        if languages is None:
            languages = [None]  # None = English/default
        
        # Calculate total tasks: sections * languages
        total_tasks = total_sections * len(languages)
        
        # Initialize progress
        if tracker:
            tracker.update_progress(
                category="avatar_generation", 
                completed=0, 
                total=total_tasks, 
                failed=0,
                message=f"Starting avatar generation for {len(languages)} language(s)..."
            )
        
        avatar_dir = Path(output_dir)
        save_dir = avatar_dir / "avatars"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "queued": [],
            "skipped": [],
            "failed": [],
            "completed": []
        }

        if not sections:
            print(f"[AVATAR] Warning: No sections found in presentation to process.")
            return results

        BATCH_SIZE = 3
        section_batches = [sections[i:i + BATCH_SIZE] for i in range(0, len(sections), BATCH_SIZE)]
        
        print(f"[AVATAR] Initiating synchronous processing in {len(section_batches)} batches...")
        
        
        # Load state for recovery (if available)
        state_file = Path(output_dir) / "avatar_analysis.json"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except:
                pass

        # Helper to submit
        def _submit_single_section(section, job_id, save_dir, language=None, speaker=None, state=None):
            sec_id = section.get("section_id")
            output_filename = f"section_{sec_id}_avatar.mp4"
            
            # Create language-specific subdirectory if language is specified
            if language:
                lang_save_dir = save_dir / language
                lang_save_dir.mkdir(parents=True, exist_ok=True)
                output_path = lang_save_dir / output_filename
            else:
                output_path = save_dir / output_filename
            
            # 1. Check for existing
            if output_path.exists() and output_path.stat().st_size > 1000:
                # Try to preserve existing task_id if known
                existing_tid = section.get("avatar_task_id") or section.get("avatar_id")
                existing_vimeo = section.get("vimeo_url")
                existing_b2 = section.get("b2_url")
                
                # RECOVERY: If missing in section but present in state, use state
                if not (existing_tid and existing_vimeo and existing_b2) and state and "tasks" in state:
                    for tid, tinfo in state["tasks"].items():
                        if str(tinfo.get("section_id")) == str(sec_id):
                            if not existing_tid: existing_tid = tid
                            if not existing_vimeo: existing_vimeo = tinfo.get("vimeo_url")
                            if not existing_b2: existing_b2 = tinfo.get("b2_url")
                            break
                
                # If we recovered at least the task_id, we can skip generation
                if existing_tid:
                    return {
                        "status": "skipped", 
                        "section_id": sec_id, 
                        "language": language, 
                        "reason": "exists", 
                        "output_path": str(output_path), 
                        "task_id": existing_tid,
                        "vimeo_url": existing_vimeo,
                        "b2_url": existing_b2
                    }
                else:
                    # SELF-HEALING: File exists but no metadata found in section or state.
                    # We MUST regenerate to get a valid task_id and metadata.
                    print(f"[AVATAR-FIX] Sec {sec_id} file exists but missing metadata. Forcing regeneration.")

            # 2. Extract Text

            # 2. Extract Text
            narration_text = ""
            if "narration_segments" in section: # V1.5 Preferred
                segments = section["narration_segments"]
                narration_text = " ".join([str(seg.get("text", "") or "") for seg in segments])
            elif "narration" in section:
                narr = section["narration"]
                if isinstance(narr, dict):
                    narration_text = narr.get("full_text", "")
                else:
                    narration_text = str(narr)
                
                if not narration_text:
                     # Fallback
                     if isinstance(narr, dict):
                         narration_text = " ".join([str(s.get("text", "") or "") for s in narr.get("segments", [])])

            if not narration_text or not narration_text.strip():
                return {"status": "skipped", "section_id": sec_id, "language": language, "reason": "empty_text"}
            
            # 3. Submit with language and speaker
            lang_str = f" [{language}]" if language else ""
            print(f"[AVATAR] Submitting Sec {sec_id}{lang_str}...")
            res = self.generate_avatar_video(narration_text, job_id, sec_id, language=language, speaker=speaker)
            # Handle both task_id dict and direct error dict
            if "task_id" in res:
                return {
                    "status": "queued",
                    "section_id": sec_id,
                    "language": language,
                    "task_id": res["task_id"],
                    "output_path": str(output_path)
                }
            else:
                 return {"status": "failed", "section_id": sec_id, "language": language, "error": res.get("error", "Unknown")}

        # --- BATCH LOOP ---
        for batch_idx, batch in enumerate(section_batches):
            print(f"\n[AVATAR] === Processing Batch {batch_idx + 1}/{len(section_batches)} (Size: {len(batch)}) ===")
            
            current_batch_tasks = []
            
            # 1. SUBMIT BATCH for all languages
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                # Submit tasks for each section and language combination
                futures = {}
                for sec in batch:
                    for lang in languages:
                        future = executor.submit(_submit_single_section, sec, job_id, save_dir, language=lang, speaker=speaker, state=state)
                        futures[future] = (sec, lang)
                
                for future in as_completed(futures):
                    try:
                        res = future.result()
                        status = res.get("status")
                        if status == "queued":
                            current_batch_tasks.append(res)
                            results["queued"].append(res)
                        elif status == "skipped":
                            results["skipped"].append(res)
                            lang_str = f" [{res.get('language')}]" if res.get('language') else ""
                            print(f"[AVATAR] - Sec {res.get('section_id')}{lang_str} skipped.")
                            if "output_path" in res:
                                 self._update_artifacts(output_dir, res["section_id"], res["output_path"],
                                                      language=res.get("language"), speaker=speaker, 
                                                      task_id=res.get("task_id"),
                                                      vimeo_url=res.get("vimeo_url"),
                                                      b2_url=res.get("b2_url"))
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_tasks,
                                    failed=len(results["failed"]),
                                    message=f"Skipped Section {res.get('section_id')}{lang_str}"
                                )
                        else:
                            results["failed"].append(res)
                            lang_str = f" [{res.get('language')}]" if res.get('language') else ""
                            print(f"[AVATAR] x Sec {res.get('section_id')}{lang_str} submission failed.")
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_tasks,
                                    failed=len(results["failed"]),
                                    message=f"Failed to submit Section {res.get('section_id')}{lang_str}"
                                )
                    except Exception as e:
                         print(f"[AVATAR] Submission Ex: {e}")
            
            if not current_batch_tasks:
                print(f"[AVATAR] Batch {batch_idx + 1} finished (No active tasks).")
                continue
                
            # 2. POLL & WAIT FOR BATCH
            print(f"[AVATAR] Waiting for {len(current_batch_tasks)} tasks to complete...")
            
            # Map task_id -> info
            active_map = {t["task_id"]: t for t in current_batch_tasks}
            completed_in_batch = set()
            
            # Timeout logic: e.g., 20 minutes max per batch
            start_wait = time.time()
            max_wait_sec = 1200 
            
            while len(completed_in_batch) < len(active_map):
                if time.time() - start_wait > max_wait_sec:
                    print(f"[AVATAR] TIMEOUT waiting for batch {batch_idx+1}.")
                    break
                
                # Check all active not yet completed
                pending_ids = [tid for tid in active_map if tid not in completed_in_batch]
                
                for tid in pending_ids:
                    status_res = self.check_status(tid)
                    status = status_res.get("status")
                    
                    # Support both 'completed' and 'success'
                    is_success = (status == "completed" or (status_res.get("result", {}).get("success") is True))
                    
                    if is_success:
                        print(f"[AVATAR] Task {tid} COMPLETED. Downloading...")
                        # Download immediately
                        out_path = active_map[tid]["output_path"]
                        success = self.download_video(tid, out_path)
                        
                        # Extract Vimeo and B2 URLs if available
                        raw = status_res.get("raw_response", {})
                        vimeo_url = raw.get("vimeo_url")
                        b2_url = raw.get("b2_url")

                        # Get duration from status if available
                        duration = 0.0
                        try:
                            raw_duration = float(raw.get("result", {}).get("data", {}).get("video_duration", 0.0))
                            # BUGFIX: API returns duration in milliseconds, not seconds.
                            # Sanity check: if value > 1000, it must be in ms — convert to seconds.
                            if raw_duration > 1000:
                                duration = raw_duration / 1000.0
                                logger.info(f"[AVATAR] Converted duration from ms to s: {raw_duration}ms -> {duration:.2f}s")
                            else:
                                duration = raw_duration
                        except:
                            pass

                        if success:
                            results["completed"].append(active_map[tid])
                            completed_in_batch.add(tid)
                            # Pass language and speaker to _update_artifacts
                            lang = active_map[tid].get("language")
                            self._update_artifacts(output_dir, active_map[tid]["section_id"], out_path, duration, 
                                                  vimeo_url=vimeo_url, b2_url=b2_url,
                                                  language=lang, speaker=speaker, task_id=tid)
                            
                            lang_str = f" [{active_map[tid].get('language')}]" if active_map[tid].get('language') else ""
                            if tracker:
                                tracker.update_progress(
                                    category="avatar_generation",
                                    completed=len(results["completed"]) + len(results["skipped"]),
                                    total=total_tasks,
                                    failed=len(results["failed"]),
                                    message=f"Completed Section {active_map[tid]['section_id']}{lang_str}"
                                )
                        else:
                            print(f"[AVATAR] Failed to download {tid}")
                            # Treat as completed (but failed download) to stop polling
                            completed_in_batch.add(tid) 
                            
                    elif status == "failed" or status == "not_found":
                        print(f"[AVATAR] Task {tid} {status.upper()} on server.")
                        results["failed"].append(active_map[tid])
                        completed_in_batch.add(tid)
                        
                        if tracker:
                            tracker.update_progress(
                                category="avatar_generation",
                                completed=len(results["completed"]) + len(results["skipped"]),
                                total=total_tasks,
                                failed=len(results["failed"]),
                                message=f"Task {tid} failed"
                            )
                    
                    # If 'queued' or 'processing', just wait
                
                if len(completed_in_batch) < len(active_map):
                    time.sleep(5) # Poll interval
            
            print(f"[AVATAR] Batch {batch_idx+1} Done.")
            
        final_msg = f"[AVATAR] Job Complete. Queued: {len(results['queued'])}, Completed/Downloaded: {len(results['completed'])}, Skipped: {len(results['skipped'])}, Failed: {len(results['failed'])}"
        logger.info(final_msg)
        print(final_msg)
        
        if results["failed"]:
            print(f"[AVATAR] Critical: {len(results['failed'])} tasks failed.")
            for f in results["failed"]:
                print(f"  - Section {f.get('section_id')}: {f.get('error', 'Unknown Error')}")
                
        return results

    def submit_quiz_clips(self, presentation: Dict[str, Any], job_id: str, output_dir: str,
                          language: str = None, speaker: str = None) -> Dict[str, Any]:
        """
        V3: Generate 3 avatar clips per quiz question.

        For each quiz section and each question, submits 4 separate avatar jobs:
          1. question clip     — avatar reads the question
          2. correct clip      — avatar reacts "Correct! [explanation]"
          3. wrong clip        — avatar reacts "Not quite. The answer is [correct_option]..."
          4. explanation clip  — avatar explains WHY the answer is correct (plays after both correct and wrong)

        Output filenames (stored under avatars/{language or 'en'}/):
          quiz_{section_id}_q{n}_question.mp4
          quiz_{section_id}_q{n}_correct.mp4
          quiz_{section_id}_q{n}_wrong.mp4

        Updates presentation.json section.questions[n].avatar_clips with relative paths.

        Returns:
            Dict with keys: submitted, completed, failed
        """
        lang_dir = language or "en"
        save_dir = Path(output_dir) / "avatars" / lang_dir
        save_dir.mkdir(parents=True, exist_ok=True)

        sections = presentation.get("sections", [])
        quiz_sections = []
        for s in sections:
            if s.get("section_type") == "quiz" or s.get("type") == "quiz":
                quiz_sections.append(s)
            elif "understanding_quiz" in s:
                if not s.get("questions"):
                    s["questions"] = [s.get("understanding_quiz")]
                quiz_sections.append(s)

        results = {"submitted": 0, "completed": 0, "failed": 0, "clips": []}

        if not quiz_sections:
            logger.info("[AVATAR-QUIZ] No quiz sections found — skipping.")
            return results

        CLIP_TYPES = ["question", "correct", "wrong", "explanation"]

        for section in quiz_sections:
            sec_id = section.get("section_id", "0")
            questions = section.get("questions", [])

            for q_idx, q in enumerate(questions):
                q_id = q.get("question_id", f"q{q_idx + 1}")
                narr = q.get("narration", {})

                scripts = {
                    "question":    narr.get("question_script", ""),
                    "correct":     narr.get("correct_script", ""),
                    "wrong":       narr.get("wrong_script", ""),
                    "explanation": narr.get("explanation_script", ""),
                }

                # Auto-generate fallback scripts if missing
                if not scripts["question"]:
                    scripts["question"] = q.get("question_text", "Here is your quiz question.")
                if not scripts["correct"]:
                    correct_key = q.get("correct_option", "")
                    correct_txt = q.get("options", {}).get(correct_key, "")
                    expl = q.get("explanation", "")
                    scripts["correct"] = f"Excellent! That is correct. The answer is {correct_txt}. {expl}"
                if not scripts["wrong"]:
                    correct_key = q.get("correct_option", "")
                    correct_txt = q.get("options", {}).get(correct_key, "")
                    scripts["wrong"] = f"Not quite. The correct answer is option {correct_key}: {correct_txt}. Let me explain why."
                if not scripts["explanation"]:
                    expl = q.get("explanation", "")
                    correct_key = q.get("correct_option", "")
                    correct_txt = q.get("options", {}).get(correct_key, "")
                    scripts["explanation"] = expl or f"The correct answer is {correct_key}: {correct_txt}."

                clip_paths: Dict[str, str] = {}

                for clip_type in CLIP_TYPES:
                    script_text = scripts[clip_type]
                    if not script_text:
                        logger.warning(f"[AVATAR-QUIZ] Sec {sec_id} Q{q_idx} {clip_type}: empty script, skipping.")
                        continue

                    filename = f"quiz_{sec_id}_{q_id}_{clip_type}.mp4"
                    out_path = save_dir / filename
                    rel_path = f"avatars/{lang_dir}/{filename}"

                    # Skip if already exists
                    if out_path.exists() and out_path.stat().st_size > 1000:
                        logger.info(f"[AVATAR-QUIZ] {filename} already exists, skipping.")
                        clip_paths[clip_type] = rel_path
                        continue

                    # Submit avatar job
                    logger.info(f"[AVATAR-QUIZ] Submitting {clip_type} clip for Sec {sec_id} Q{q_id}...")
                    res = self.generate_avatar_video(script_text, job_id, sec_id,
                                                     language=language, speaker=speaker)
                    if "task_id" not in res:
                        logger.error(f"[AVATAR-QUIZ] Submit failed: {res.get('error', 'Unknown')}")
                        results["failed"] += 1
                        continue

                    task_id = res["task_id"]
                    results["submitted"] += 1

                    # Poll until done (blocking, per clip)
                    max_wait = 600  # 10 min max per clip
                    start = time.time()
                    downloaded = False

                    while time.time() - start < max_wait:
                        status_res = self.check_status(task_id)
                        status = status_res.get("status")

                        is_success = (
                            status == "completed"
                            or (status_res.get("result", {}).get("success") is True)
                        )

                        if is_success:
                            ok = self.download_video(task_id, str(out_path))
                            if ok:
                                clip_paths[clip_type] = rel_path
                                results["completed"] += 1
                                downloaded = True
                            else:
                                results["failed"] += 1
                            break
                        elif status in ("failed", "not_found"):
                            logger.error(f"[AVATAR-QUIZ] Task {task_id} failed on server.")
                            results["failed"] += 1
                            break

                        time.sleep(5)

                    if not downloaded and clip_type in CLIP_TYPES and clip_type not in clip_paths:
                        logger.warning(f"[AVATAR-QUIZ] Clip {filename} timed out or failed.")

                # Patch question in presentation.json with relative paths
                if clip_paths:
                    q["avatar_clips"] = clip_paths
                    results["clips"].append({
                        "section_id": sec_id,
                        "question_id": q_id,
                        "clips": clip_paths
                    })

            # Save updated presentation.json after each quiz section
            pres_path = Path(output_dir) / "presentation.json"
            if pres_path.exists():
                try:
                    with presentation_lock:
                        with open(pres_path, "r", encoding="utf-8") as f:
                            pres_data = json.load(f)
                        for s in pres_data.get("sections", []):
                            if str(s.get("section_id")) == str(sec_id):
                                s["questions"] = section.get("questions", s.get("questions", []))
                                break
                        with open(pres_path, "w", encoding="utf-8") as f:
                            json.dump(pres_data, f, indent=2)
                    logger.info(f"[AVATAR-QUIZ] Updated presentation.json quiz clips for Sec {sec_id}")
                except Exception as e:
                    logger.error(f"[AVATAR-QUIZ] Failed to update presentation.json: {e}")

        logger.info(f"[AVATAR-QUIZ] Done. Submitted: {results['submitted']}, "
                    f"Completed: {results['completed']}, Failed: {results['failed']}")
        return results

    def submit_all_jobs(self, presentation: Dict[str, Any], job_id: str, output_dir: str, 
                       target_sections: Optional[List[str]] = None, force: bool = False, 
                       tracker: Optional[AnalyticsTracker] = None,
                       languages: list = None, speaker: str = None) -> Dict[str, Any]:
        """
        New "Submit All" strategy:
        - target_sections: List of section_ids to process (None = all)
        - force: If True, bypasses existence check and re-submits
        - languages (list, optional): List of language codes for multi-language generation
        - speaker (str, optional): Voice ID for non-English languages
        """
        lang_info = f" for {len(languages)} language(s)" if languages else ""
        logger.info(f"[AVATAR-ALL] Starting 'Submit All' strategy for Job {job_id} (Target: {target_sections}, Force: {force}){lang_info}")
        sections = presentation.get("sections", [])
        job_path = Path(output_dir)
        state_file = job_path / "avatar_analysis.json"
        save_dir = job_path / "avatars"
        save_dir.mkdir(parents=True, exist_ok=True)

        # 1. Recover state if exists (Reset if force is global?)
        state = {"job_id": job_id, "tasks": {}}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
                logger.info(f"[AVATAR-ALL] Recovered {len(state['tasks'])} tasks from state file.")
            except Exception as e:
                logger.error(f"[AVATAR-ALL] Failed to load state file: {e}")

        # 2. Submit sections
        submitted_now = 0
        for section in sections:
            sec_id = str(section.get("section_id"))
            
            # Scope check
            if target_sections and sec_id not in [str(s) for s in target_sections]:
                continue
            
            # Check if already completed in state (Honor force)
            output_filename = f"section_{sec_id}_avatar.mp4"
            output_path = save_dir / output_filename
            
            task_entry = None
            for tid, tinfo in list(state["tasks"].items()):
                if str(tinfo.get("section_id")) == sec_id:
                    # If forcing this section, remove it from state so it re-submits
                    if force:
                        del state["tasks"][tid]
                    else:
                        task_entry = tid
                    break
            
            if task_entry:
                continue # Already tracking

            # SMART CHECK: If file is missing or corrupt, we MUST generate/submit (Unless forcing)
            file_missing = not output_path.exists() or output_path.stat().st_size < 1000
            
            if file_missing or force:
                # Extract Text
                narration_text = ""
                if "narration_segments" in section:
                    narration_text = " ".join([str(seg.get("text", "") or "") for seg in section["narration_segments"]])
                elif "narration" in section:
                    narr = section["narration"]
                    if isinstance(narr, dict):
                        narration_text = narr.get("full_text", "") or " ".join([str(s.get("text", "") or "") for s in narr.get("segments", [])])
                    else:
                        narration_text = str(narr)
                
                if not narration_text.strip():
                    continue

                res = self.generate_avatar_video(narration_text, job_id, int(sec_id), language=languages[0] if languages else None, speaker=speaker)
                if "task_id" in res:
                    tid = res["task_id"]
                    state["tasks"][tid] = {
                        "section_id": int(sec_id),
                        "task_id": tid,
                        "output_path": str(output_path),
                        "status": "queued"
                    }
                    submitted_now += 1
                    logger.info(f"[AVATAR-ALL] Submitted Sec {sec_id} -> Task {tid}")
                else:
                    logger.error(f"[AVATAR-ALL] Failed to submit Sec {sec_id}: {res.get('error')}")

        if submitted_now > 0:
            state_file.write_text(json.dumps(state, indent=2))
            logger.info(f"[AVATAR-ALL] Saved state for {submitted_now} new tasks.")

        # 3. Polling Loop
        active_tasks = [tid for tid, info in state["tasks"].items() if info.get("status") != "completed"]
        if not active_tasks:
            logger.info("[AVATAR-ALL] No active tasks to poll.")
            return state

        logger.info(f"[AVATAR-ALL] Entering polling loop for {len(active_tasks)} tasks (Interval: 30s)")
        start_time = time.time()
        timeout = 3600 # 1 hour global timeout
        
        while active_tasks and (time.time() - start_time < timeout):
            print(f"\n[AVATAR-ALL] Polling {len(active_tasks)} active tasks. Elapsed: {int(time.time() - start_time)}s", flush=True)
            still_active = []
            for tid in active_tasks:
                try:
                    status_res = self.check_status(tid)
                    status = status_res.get("status")
                    print(f"[AVATAR-ALL] Task {tid} status: {status}", flush=True)
                    
                    # API returns 'completed' or 'success' depending on version/path
                    if status == "completed" or (status_res.get("result", {}).get("success") is True):
                        print(f"[AVATAR-ALL] Task {tid} COMPLETED. Downloading...", flush=True)
                        info = state["tasks"][tid]
                        if self.download_video(tid, info["output_path"]):
                            # Extract Vimeo and B2 details
                            vimeo_url = None
                            b2_url = None
                            try:
                                raw = status_res.get("raw_response", {})
                                vimeo_url = raw.get("vimeo_url")
                                b2_url = raw.get("b2_url")
                                duration = float(raw.get("result", {}).get("data", {}).get("video_duration", 0.0))
                                # THREEJS-001 FIX: HeyGen API returns duration in milliseconds.
                                # The primary poll loop (line ~589) already has this guard — apply it here too.
                                if duration > 1000:
                                    duration = duration / 1000.0
                                    logger.info(f"[AVATAR-ALL] Converted duration ms→s: {duration*1000:.0f}ms → {duration:.2f}s")
                            except:
                                duration = 0.0
                                
                            self._update_artifacts(output_dir, info["section_id"], info["output_path"], duration, vimeo_url, b2_url, task_id=tid)
                            info["status"] = "completed"
                            info["vimeo_url"] = vimeo_url
                            info["b2_url"] = b2_url
                            logger.info(f"[AVATAR-ALL] Sec {info['section_id']} DONE.")
                        else:
                            still_active.append(tid) # Retry download next loop
                    elif status == "failed" or status == "not_found":
                        logger.error(f"[AVATAR-ALL] Task {tid} {status.upper()} on server.")
                        state["tasks"][tid]["status"] = "failed"
                        # No need to keep polling a terminal failure
                    else:
                        still_active.append(tid)
                except Exception as e:
                    logger.error(f"[AVATAR-ALL] Error checking task {tid}: {e}")
                    still_active.append(tid)

            active_tasks = still_active
            if active_tasks:
                state_file.write_text(json.dumps(state, indent=2))
                time.sleep(30) # User requested 30s poll

        # Cleanup if all done
        if not active_tasks:
            logger.info("[AVATAR-ALL] All tasks finished. Cleaning up state file.")
            try: state_file.unlink()
            except: pass
        else:
            logger.warning(f"[AVATAR-ALL] Polling timed out with {len(active_tasks)} tasks still active.")

        return state
