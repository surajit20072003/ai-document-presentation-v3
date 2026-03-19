import os
import time
import logging
import asyncio
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from render.wan.wan_client import WANClient, WanSafetyError, WanFatalError
from core.llm_client import openrouter

logger = logging.getLogger(__name__)


class KieBatchGenerator:
    """
    Batched generator for Kie.ai WAN API.
    Handles rate limits (15 concurrent, 15s interval) and parallel polling.
    """

    BATCH_SIZE = 5
    BATCH_INTERVAL = 2

    def __init__(
        self, api_key: Optional[str] = None, status_file_path: Optional[str] = None
    ):
        self.client = WANClient(api_key)
        self.pending_tasks = []  # List of (beat_id, task_id, output_path)
        self.status_file_path = status_file_path  # NEW: Path to wan_status.json

    def _rewrite_prompt(
        self, original_prompt: str, feedback: str = None, is_safety_fix: bool = False
    ) -> str:
        """Rewrite prompt using LLM for safety or user feedback."""
        try:
            # HARD SAFETY RULES for System Prompt
            safety_rules = """
🔒 WAN VIDEO PROMPT HARD SAFETY RULES (MANDATORY)
1. NEVER use close-up or extreme framing for humans.
   - DO NOT use: "close-up", "extreme close-up", "macro", "tight framing"
   - ALWAYS use: "medium shot", "medium-wide shot", or "wide shot"
2. NEVER explicitly mention human body parts.
   - DO NOT mention: hands, eyes, face, skin, fingers
   - Describe actions indirectly (e.g., "writing at a desk", "focused posture")
3. NEVER use age-descriptive human terms.
   - DO NOT use: young, child, girl, boy, young woman
   - ALWAYS use: "adult person" or "individual"
4. NEVER use cinematic intimacy language.
   - DO NOT use: rack focus, lingering shot, intimate, sensual, dramatic zoom on person
   - Use neutral camera behavior: steady camera, fixed framing, gentle focus shift
5. Style disclaimers DO NOT override safety.
   - Phrases like "educational", "documentary", or "non-sexual" do NOT make unsafe prompts valid.
6. NO SPECIFIC GENDER/AGE for generic humans.
   - Convert "woman", "man", "girl", "boy" to "individual" or "adult person".
7. NO CLOTHING DESCRIPTIONS that could be misinterpreted.
   - Use: "professional attire", "simple clothing", or omit clothing details entirely.
"""
            if is_safety_fix:
                sys_prompt = f"You are a safety assistant. Rewrite this video prompt to be safe, educational, and documentary-style. remove any potential NSFW triggers. Follow these HARD SAFETY RULES:{safety_rules} Return ONLY the new prompt."
            elif feedback:
                sys_prompt = f"You are a video prompt improver. Rewrite this prompt to incorporate the user's feedback: '{feedback}'. Keep it safe and documentary-style. Return ONLY the new prompt."
            else:
                return original_prompt

            response = openrouter.chat.completions.create(
                model="google/gemini-2.5-flash",  # Fast model for rewrites
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": original_prompt},
                ],
            )
            new_prompt = response.choices[0].message.content.strip()
            # Remove quotes if present
            if new_prompt.startswith('"') and new_prompt.endswith('"'):
                new_prompt = new_prompt[1:-1]
            logger.info(
                f"[WAN Safety] Prompt rewritten: '{original_prompt[:30]}...' -> '{new_prompt[:30]}...'"
            )
            return new_prompt
        except Exception as e:
            logger.error(f"[WAN Safety] LLM Rewrite failed: {e}")
            return original_prompt  # Fallback

    def _update_status(self, state, **kwargs):
        """Update wan_status.json with current progress and pending task_ids for recovery."""
        if not self.status_file_path:
            return

        try:
            from datetime import datetime
            import json

            status = {
                "state": state,
                "total_beats": kwargs.get("total_beats", 0),
                "completed_beats": kwargs.get("completed_beats", 0),
                "failed_beats": kwargs.get("failed_beats", 0),
                "progress_percent": kwargs.get("progress_percent", 0),
                "updated_at": datetime.now().isoformat(),
                "details": kwargs.get("details", {}),
            }

            if "started_at" in kwargs:
                status["started_at"] = kwargs["started_at"]

            # NEW: Save pending_tasks for crash recovery (includes task_ids)
            if kwargs.get("save_pending_tasks", False) and self.pending_tasks:
                status["pending_tasks"] = [
                    {
                        "beat_id": t["beat_id"],
                        "task_id": t["task_id"],
                        "output_path": t["output_path"],
                        "prompt": t.get("final_prompt", t.get("prompt")),
                        "duration": t.get("duration", 5),
                    }
                    for t in self.pending_tasks
                ]

            with open(self.status_file_path, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"[WAN Status] Failed to update status file: {e}")

    def _load_pending_tasks(self) -> List[Dict]:
        """Load pending tasks with task_ids from wan_status.json for recovery."""
        if not self.status_file_path or not os.path.exists(self.status_file_path):
            return []

        try:
            import json

            with open(self.status_file_path, "r", encoding="utf-8") as f:
                status = json.load(f)

            pending = status.get("pending_tasks", [])
            if pending:
                logger.info(
                    f"[WAN Recovery] Found {len(pending)} pending tasks from previous session"
                )
            return pending
        except Exception as e:
            logger.error(f"[WAN Recovery] Failed to load pending tasks: {e}")
            return []

    def resume_polling(self) -> Dict:
        """
        Resume polling for orphaned tasks from a previous session.

        Call this before generate_batch() to recover videos that may have
        completed on Kie.ai while your server was down.

        Returns:
            Dict[beat_id -> {"path": str|None, "prompt": str, "error": str|None}]
        """
        saved_tasks = self._load_pending_tasks()
        if not saved_tasks:
            logger.info("[WAN Recovery] No pending tasks to resume")
            return {}

        logger.info(
            f"[WAN Recovery] Resuming polling for {len(saved_tasks)} orphaned tasks..."
        )

        # Filter out tasks where video already exists on disk
        tasks_to_poll = []
        already_done = {}
        for task in saved_tasks:
            output_path = task.get("output_path")
            beat_id = task.get("beat_id")
            if (
                output_path
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 100000
            ):
                # Video file exists and is > 100KB, consider it done
                logger.info(
                    f"[WAN Recovery] {beat_id} already has video file, skipping"
                )
                already_done[beat_id] = {
                    "path": output_path,
                    "prompt": task.get("prompt"),
                    "error": None,
                }
            else:
                tasks_to_poll.append(task)

        if not tasks_to_poll:
            logger.info("[WAN Recovery] All tasks already have video files")
            # Clear pending_tasks from status file
            self._update_status(
                "resumed_complete", details={"recovered": list(already_done.keys())}
            )
            return already_done

        # Poll the remaining tasks
        self.pending_tasks = tasks_to_poll
        logger.info(f"[WAN Recovery] Polling {len(tasks_to_poll)} tasks...")

        results = self._poll_all_tasks()
        results.update(already_done)

        # Update status file - clear pending_tasks on completion
        completed = [bid for bid, r in results.items() if r and r.get("path")]
        failed = [bid for bid, r in results.items() if not r or not r.get("path")]

        self._update_status(
            "resumed_complete" if not failed else "resumed_with_errors",
            completed_beats=len(completed),
            failed_beats=len(failed),
            details={
                "recovered": completed,
                "failed": failed,
                "errors": {
                    bid: results.get(bid, {}).get("error", "Unknown") for bid in failed
                },
            },
        )

        logger.info(
            f"[WAN Recovery] Resume complete: {len(completed)} recovered, {len(failed)} failed"
        )

        # IMPORTANT: Clear pending_tasks after resume to prevent mixing with new submissions
        self.pending_tasks = []

        return results

    def _is_placeholder_video(self, video_path: str, expected_duration: int) -> bool:
        """
        Detect if a video is a placeholder by checking duration.

        Args:
            video_path: Path to video file
            expected_duration: Expected duration from narration (5/10/15 seconds)

        Returns:
            True if video is a placeholder (duration ≤ 2 seconds)
        """
        if not os.path.exists(video_path):
            return False

        try:
            from moviepy.editor import VideoFileClip

            with VideoFileClip(video_path) as clip:
                actual_duration = clip.duration

            # Placeholder detection: duration ≤ 2 seconds when expecting >= 5
            if actual_duration <= 2 and expected_duration >= 5:
                print(
                    f"[WAN] Placeholder detected: {video_path} (duration={actual_duration}s, expected={expected_duration}s)"
                )
                return True

            return False
        except Exception as e:
            logger.error(f"[WAN] Failed to check video duration for {video_path}: {e}")
            # If we can't determine, treat very small files as placeholders
            file_size = os.path.getsize(video_path)
            return file_size < 100000  # < 100KB is likely placeholder

    def generate_batch(
        self,
        beats: List[Dict],
        output_dir: str,
        user_feedback: str = None,
        resume_first: bool = True,
    ):
        """
        Process a list of beats in batches.
        Each beat in 'beats' should have: beat_id, prompt, duration_hint

        Args:
            beats: List of beat dicts with beat_id, prompt, duration_hint
            output_dir: Directory to save videos
            user_feedback: Optional feedback to rewrite prompts
            resume_first: If True, check for orphaned tasks from previous session first
        """
        if not beats:
            return {}

        os.makedirs(output_dir, exist_ok=True)
        results = {}

        # NEW: Resume orphaned tasks from previous session if any
        if resume_first:
            recovered = self.resume_polling()
            if recovered:
                logger.info(
                    f"[WAN] Recovered {len(recovered)} videos from previous session"
                )
                results.update(recovered)
                # Filter out beats that were already recovered
                recovered_ids = set(recovered.keys())
                beats = [b for b in beats if b.get("beat_id") not in recovered_ids]
                if not beats:
                    logger.info(
                        "[WAN] All beats recovered from previous session, nothing to generate"
                    )
                    return results

        # NEW: Initialize status tracking
        from datetime import datetime

        started_at = datetime.now().isoformat()
        self._update_status(
            "processing",
            total_beats=len(beats),
            completed_beats=0,
            failed_beats=0,
            progress_percent=0,
            started_at=started_at,
            details={
                "pending": [b["beat_id"] for b in beats],
                "in_progress": [],
                "completed": [],
                "failed": [],
                "errors": {},
            },
        )

        # 1. Submission Phase - clear pending_tasks first to ensure clean state
        self.pending_tasks = []
        for i in range(0, len(beats), self.BATCH_SIZE):
            batch = beats[i : i + self.BATCH_SIZE]
            logger.info(
                f"[KieBatch] Submitting batch {i // self.BATCH_SIZE + 1} ({len(batch)} items)..."
            )

            for beat in batch:
                beat_id = beat.get("beat_id")
                original_prompt = (
                    beat.get("prompt")
                    or beat.get("video_prompt")
                    or beat.get("wan_prompt")
                    or ""
                )
                # TODO: In future, support 'duration' key as well. For now, rely on duration_hint or default 15.
                duration = int(beat.get("duration_hint", 15))
                output_path = os.path.join(output_dir, f"{beat_id}.mp4")

                # GRANULAR RETRY: Check if file exists and is valid (>0 bytes)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    # NEW: Check if it's a placeholder video
                    if self._is_placeholder_video(output_path, duration):
                        print(
                            f"[WAN] Placeholder detected for {beat_id}, will retry..."
                        )
                        # Delete placeholder to force regeneration
                        try:
                            os.remove(output_path)
                            print(f"[WAN] Deleted placeholder: {output_path}")
                            # Update status to show retry attempt
                            # Note: Status will be updated again in polling phase
                        except Exception as e:
                            logger.error(
                                f"[WAN] Failed to delete placeholder {output_path}: {e}"
                            )
                            # If deletion fails, treat as existing valid file to avoid infinite retry
                            results[beat_id] = {
                                "path": output_path,
                                "prompt": original_prompt,
                            }
                            continue
                    else:
                        # Valid video exists, skip
                        print(f"[WAN] Skipping existing beat: {beat_id}")
                        # Pre-populate result immediately - return dict with path and original prompt
                        results[beat_id] = {
                            "path": output_path,
                            "prompt": original_prompt,
                        }
                        continue

                # Pre-process prompt if user feedback provided
                current_prompt = original_prompt
                if user_feedback:
                    logger.info(f"[WAN] Applying user feedback to prompt for {beat_id}")
                    current_prompt = self._rewrite_prompt(
                        original_prompt, feedback=user_feedback
                    )

                print(
                    f"[WAN] Submitting Beat: {beat_id} | Prompt: {current_prompt[:60]}... | Duration: {duration}s"
                )

                # Try up to 3 times for Safety Errors
                task_created = False
                for attempt in range(3):
                    try:
                        # Attempt to create task
                        prompt_to_use = current_prompt

                        task_id = self._create_task(prompt_to_use, duration)
                        if task_id:
                            self.pending_tasks.append(
                                {
                                    "beat_id": beat_id,
                                    "task_id": task_id,
                                    "output_path": output_path,
                                    "prompt": prompt_to_use,
                                    "final_prompt": prompt_to_use,
                                    "duration": duration,
                                    "is_retry": attempt > 0,
                                }
                            )
                            task_created = True
                            if attempt > 0:
                                logger.info(
                                    f"[WAN] Safety retry {attempt}/3 successful for {beat_id}"
                                )
                            break  # Success, exit loop
                        else:
                            logger.error(
                                f"[KieBatch] Failed to create task for {beat_id} (Attempt {attempt + 1}/3)"
                            )

                    except WanSafetyError as e:
                        logger.warning(
                            f"[WAN] Safety Error for {beat_id} (Attempt {attempt + 1}/3): {e}"
                        )
                        if attempt < 2:
                            logger.info(
                                f"[WAN] Rewriting prompt for safety retry {attempt + 1}..."
                            )
                            current_prompt = self._rewrite_prompt(
                                current_prompt, is_safety_fix=True
                            )
                            continue  # Try next attempt
                        else:
                            logger.error(
                                f"[WAN] All 3 safety retries failed for {beat_id}"
                            )

                    except WanFatalError as e:
                        logger.error(
                            f"[WAN] Fatal Error for {beat_id}: {e}. Skipping retries."
                        )
                        break

                    except Exception as e:
                        logger.error(f"[KieBatch] Submission error for {beat_id}: {e}")
                        break

            # Rate limit wait between batches
            if i + self.BATCH_SIZE < len(beats):
                logger.info(
                    f"[KieBatch] Waiting {self.BATCH_INTERVAL}s before next batch..."
                )
                time.sleep(self.BATCH_INTERVAL)

        # NEW: Save pending_tasks to status file BEFORE polling (crash recovery)
        if self.pending_tasks:
            logger.info(
                f"[KieBatch] Saving {len(self.pending_tasks)} task IDs for crash recovery..."
            )
            self._update_status(
                "polling",
                total_beats=len(beats),
                completed_beats=len(results),
                failed_beats=0,
                progress_percent=int(len(results) / len(beats) * 50) if beats else 0,
                started_at=started_at,
                save_pending_tasks=True,  # This triggers saving task_ids
                details={
                    "pending": [t["beat_id"] for t in self.pending_tasks],
                    "in_progress": [],
                    "completed": list(results.keys()),
                    "failed": [],
                },
            )

        # 2. Polling Phase
        if self.pending_tasks:
            logger.info(f"[KieBatch] Polling {len(self.pending_tasks)} tasks...")
            polled_results = self._poll_all_tasks()
            results.update(polled_results)
        else:
            logger.info("[KieBatch] No pending tasks to poll.")

        # NEW: Final status update with actual error messages from Kie.ai
        completed = [
            bid
            for bid, r in results.items()
            if r and (isinstance(r, dict) and r.get("path") or isinstance(r, str))
        ]
        failed = [
            bid
            for bid, r in results.items()
            if not r or (isinstance(r, dict) and not r.get("path"))
        ]
        total = len(beats)
        progress = int((len(completed) / total * 100)) if total > 0 else 100

        # Extract actual error messages from results
        errors = {}
        for bid in failed:
            result = results.get(bid)
            if isinstance(result, dict) and result.get("error"):
                errors[bid] = result["error"]  # Actual Kie.ai error
            else:
                errors[bid] = "Generation failed (unknown error)"

        self._update_status(
            "completed" if len(failed) == 0 else "completed_with_errors",
            total_beats=total,
            completed_beats=len(completed),
            failed_beats=len(failed),
            progress_percent=progress,
            started_at=started_at,
            details={
                "pending": [],
                "in_progress": [],
                "completed": completed,
                "failed": failed,
                "errors": errors,  # Now contains actual error messages
            },
        )

        return results

    def _create_task(self, prompt: str, duration: int) -> Optional[str]:
        """Submit a single task to Kie.ai and return task_id."""
        import requests

        # Normalize duration
        valid_durations = [5, 10, 15]
        normalized_duration = 15
        if duration <= 7:
            normalized_duration = 5
        elif duration <= 12:
            normalized_duration = 10

        # Truncate prompt
        truncated_prompt = self.client._truncate_prompt(prompt, max_chars=800)

        payload = {
            "model": "wan/2-6-text-to-video",
            "input": {
                "prompt": truncated_prompt,
                "duration": str(normalized_duration),
                "resolution": "720p",
                "aspect_ratio": "16:9",
                "negative_prompt": "blurry, low quality, distorted, text overlay, watermark",
            },
        }

        try:
            response = requests.post(
                f"{self.client.base_url}/jobs/createTask",
                headers=self.client.headers,
                json=payload,
                timeout=30,
            )

            # --- ERROR MAPPING (Replicated from WANClient) ---
            if response.status_code in [422, 403, 451]:
                raise WanSafetyError(
                    f"Safety/Policy Violation ({response.status_code}): {response.text}"
                )

            if response.status_code in [401, 402, 404]:
                raise WanFatalError(
                    f"Fatal API Error ({response.status_code}): {response.text}"
                )

            if response.status_code == 400:
                err_text = response.text.lower()
                if "nsfw" in err_text or "policy" in err_text or "safety" in err_text:
                    raise WanSafetyError(f"Safety Violation (400): {response.text}")
                else:
                    raise WanFatalError(f"Bad Request (400): {response.text}")
            # ------------------------------------------------

            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("code") == 200:
                    return res_json.get("data", {}).get("taskId")
                else:
                    logger.error(f"[KieBatch] API Logic Error: {res_json}")
            else:
                logger.error(
                    f"[KieBatch] API returned {response.status_code}: {response.text}"
                )

        except (WanSafetyError, WanFatalError) as e:
            raise e  # Propagate to generate_batch for retry handling logic
        except Exception as e:
            logger.error(f"[KieBatch] CreateTask Exception: {e}")
        return None

    def _poll_all_tasks(self) -> Dict:
        """Poll all tasks in parallel using a thread pool."""
        final_results = {}
        print(f"[WAN] Starting parallel polling for {len(self.pending_tasks)} tasks...")

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_task = {
                executor.submit(self._poll_and_download, task): task
                for task in self.pending_tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                beat_id = task["beat_id"]
                try:
                    result = future.result()
                    # Result is now a dict with path, prompt, and optional error
                    if isinstance(result, dict):
                        final_results[beat_id] = result
                    else:
                        # Legacy: if string path returned directly
                        final_results[beat_id] = {
                            "path": result,
                            "prompt": task.get("final_prompt", task.get("prompt")),
                        }
                except Exception as e:
                    logger.error(f"[KieBatch] Task {beat_id} failed: {e}")
                    final_results[beat_id] = {"path": None, "error": str(e)}

        return final_results

    def _poll_and_download(self, task_info: Dict) -> Dict:
        """Poller for a single task with internal retry for safety errors.

        Returns:
            dict: {"path": str|None, "prompt": str, "error": str|None}
        """
        task_id = task_info["task_id"]
        output_path = task_info["output_path"]
        beat_id = task_info["beat_id"]
        prompt = task_info.get("final_prompt", task_info.get("prompt"))
        last_error = None

        # Loop for retries specifically during polling (Safety errors can happen here too)
        for attempt in range(3):
            try:
                # Use client's polling and download methods
                # If we are in a retry loop (attempt > 0), we must submit a NEW task first
                if attempt > 0:
                    logger.info(
                        f"[WAN Polling] Safety Retry {attempt}/3: Resubmitting task..."
                    )
                    # Rewrite prompt
                    safe_prompt = self._rewrite_prompt(
                        task_info["prompt"], is_safety_fix=True
                    )
                    # Create NEW task
                    new_task_id = self._create_task(safe_prompt, task_info["duration"])
                    if not new_task_id:
                        raise Exception("Failed to create new task for retry")

                    # Update task_id in memory for polling
                    task_id = new_task_id
                    logger.info(
                        f"[WAN Polling] Resubmitted with new task_id: {task_id}"
                    )

                # Poll
                video_url = self.client._poll_task_status(task_id)
                if video_url:
                    local_path = self.client._download_video(video_url, output_path)
                    # Use the prompt that actually worked (if rewritten)
                    final_p = safe_prompt if attempt > 0 else prompt
                    return {"path": local_path, "prompt": final_p, "error": None}

            except WanSafetyError as e:
                last_error = f"Safety/Policy Violation: {e}"
                logger.warning(
                    f"[WAN Polling] Safety Error for {beat_id} (Attempt {attempt + 1}/3): {e}"
                )

                # If we haven't exhausted retries, loop again to resubmit
                if attempt < 2:
                    continue
                else:
                    logger.error(
                        f"[WAN Polling] All 3 safety retries failed for {beat_id}"
                    )

            except Exception as e:
                last_error = str(e)
                logger.error(f"[WAN Polling] Polling error for {beat_id}: {e}")
                # Non-safety errors break the loop (we don't retry random API failures here endlessly)
                break

        # FIX: Return dict with error info instead of None
        logger.error(
            f"[WAN Polling] Beat {beat_id} FAILED - no video generated. Error: {last_error}"
        )
        return {"path": None, "prompt": prompt, "error": last_error}
