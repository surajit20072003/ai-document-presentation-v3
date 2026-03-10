# Changelog - V2.5 Director Bible Enhancements

## [February 2026] - NSFW Persistence, Blueprint Ready, WAN Status Tracking

### Added
- **[FEATURE]** **Blueprint Ready Flag:** New `blueprint_ready` field in `/job/<job_id>/status` API response
  - Allows frontend to display player link as soon as `presentation.json` is saved
  - Enables early user access while videos/avatars continue rendering in background
  - Zero breaking changes - existing `status` field remains unchanged
- **[FEATURE]** **WAN Task Tracking:** Real-time progress monitoring for WAN video generation
  - New `wan_status.json` file tracks pending/completed/failed beats
  - New endpoint: `GET /job/<job_id>/wan_status` for polling WAN progress
  - Mirrors `avatar_status.json` structure for consistency
- **[FEATURE]** **WAN Task ID Persistence & Crash Recovery:** Kie.ai task IDs now persist to `wan_status.json`
  - Saves `pending_tasks` with task_ids before polling phase begins
  - Enables `resume_polling()` to recover orphaned videos after server crashes
  - No duplicate API charges - completed videos on Kie.ai can be downloaded without regeneration
  - Automatic recovery on next job run or via dedicated recovery endpoint
- **[FEATURE]** **NSFW Prompt Persistence:** Sanitized prompts now persist to `presentation.json`
  - Auto-corrected NSFW prompts are saved back to `video_prompts` array
  - Prevents retry loops caused by original unsafe prompts persisting
  - Enhanced thread-safe updates via `presentation_lock` in `_update_presentation_safely`

### Fixed
- **[BUGFIX]** **NSFW Retry Loop:** Previously, sanitized WAN prompts were only updated in-memory, causing retries to fail with same NSFW error
  - Now writes sanitized prompts to `presentation.json` immediately after generation
  - Both video paths AND sanitized prompts saved with thread-safe locking

### Technical Details
- Modified `core/renderer_executor.py` to pass `wan_beats` to `_update_presentation_safely`
- Added `_update_status` method to `render/wan/kie_batch_generator.py`
- Blueprint ready callback added in `core/pipeline_unified.py` line 476-485
- All WAN status updates use `presentation_lock` for thread safety

---

## [Previous Updates] - Concurrency Safety & Smart Recovery

This update focuses on **Concurrency Safety**, **Stability**, and **Smart Recovery** for the presentation generation pipeline.
- **[FIX]** **Sanity Checker:** Resolved `SyntaxError: Unexpected identifier 'Html'` in `sanity_check.html`.
- **[DOCS]** **Job Lifecycle:** Updated `README.md` to define `completed_with_errors` status and clarify LLM completion vs. Job completion.

## 1. Concurrency & Sequential Safety (Global Job Pool)
- **Max Workers Enforced:** Reduced global concurrency to **2 parallel jobs** in `core/job_manager.py` for maximum stability.
- **Queued Retries:** All retry endpoints (Avatar, Manim, WAN, LTX) now use `job_manager.submit_task`.
  - *Previous Issue:* Retries spawned raw threads, bypassing the 2-job limit and causing "Thundering Herds".
  - *New Fix:* Retries now wait in the job queue, respecting the server's resource limits.
- **Sync Safety:** WAN generation in `core/pipeline_unified.py` is now synchronous to ensure worker slots are held correctly.

## 2. Smart Job Recovery
- **Goal:** Prevent loss of LLM progress during server restarts.
- **Mechanism:** On startup, `JobManager` now checks for `presentation.json` in interrupted jobs.
- **Action:** If found, the job is marked as **`completed_with_errors`** instead of `failed`.
- **User Benefit:** You no longer need to restart the entire pipeline; you can simply click "Retry" on the missing Avatar or Video sections from the Dashboard.

## 3. Asset Auto-Repair & Hotfixes
- **Asset Auto-Repair:** New endpoint `POST /api/repair-missing-assets/<job_id>` automatically restores missing avatars.
  - *Reliability:* It verifies the task status on the remote server before downloading.
  - *Cost Efficiency:* Re-downloads existing successful tasks; **no new billing/generation cost**.
- **Bulk Repair Script:** Added `scripts/repair_all_avatars.py` for one-click recovery of all historical jobs.
- **WAN Version Safety:** Implemented backward-compatibility for `submit_wan_background_job` to gracefully handle argument count mismatches during phased server updates.
- **WAN NSFW Resilience (New Logic):**
  - **Polling-Phase Detection:** Updated `WANClient` to detect safety violations *after* submission (during video generation).
  - **Auto-Retry & Rewrite:** `KieBatchGenerator` now automatically catches these flags, rewrites the prompt with "Hard Safety Rules," and resubmits once—preventing job failure.

## Files Modified
- `api/app.py`: Added `/api/repair-missing-assets/` and background task submission.
- `core/job_manager.py`: Implemented `_startup_cleanup` logic and pool management.
- `core/pipeline_unified.py`: Fixed `submit_wan_background_job` mismatch and enforced sync safety.
- `render/wan/wan_client.py`: Enhanced polling to detect safety/nsfw errors post-submission.
- `render/wan/kie_batch_generator.py`: Implemented internal retry logic for safety errors and hardened rewrite rules.
- `scripts/repair_all_avatars.py`: [NEW] Bulk recovery tool.
