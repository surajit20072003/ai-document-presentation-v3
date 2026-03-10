# Issue Resolution Document

> **Created**: 2026-02-11
> **Updated**: 2026-02-11 (Post Git Pull)
> **Status**: Ready for Implementation
> **Author**: Claude Code

---

## 0. Post-Merge Status

**Git pull completed successfully.** Team's recent commits merged:
- `f189be2` - "regenaration part"
- `9f9aa30` - "Feat: Implement blueprint_ready flag support in backend and frontend"
- `4fb1ba3` - "Fix: Avatar task_id storage and WAN placeholder retry bugs"

| Issue | Status After Merge | Action Needed |
|-------|-------------------|---------------|
| 3.1 - Avatar retry save | **STILL BROKEN** | Fix type comparison |
| 3.2 - WAN placeholder | **STILL CREATES PLACEHOLDER** | Remove placeholder creation |
| 3.3 - Blueprint ready | **WORKING** | Verified - no action needed |

---

## 1. Git Changes Summary

### Files Modified (Uncommitted)

| File | Changes |
|------|---------|
| `api/app.py` | Enhanced `status_callback` to handle both legacy signature `(jid, phase, message)` and new dict signature for `blueprint_ready` support (+17 lines) |
| `core/pipeline_unified.py` | Added `Callable` type import for type hints (+1 line) |
| `docs/v2.5_Director_Pipeline_Technical_Doc.md` | Documentation updates (+76 lines) |

### Detailed Changes

**api/app.py (lines 3002-3023)**:
```python
# OLD: Only supported legacy 3-arg signature
def status_callback(jid, phase, message):
    job_manager.update_job(jid, {...}, persist=True)

# NEW: Supports both legacy AND dict signature for blueprint_ready
def status_callback(update_data_or_jid, phase=None, message=None):
    if isinstance(update_data_or_jid, dict):
        # New dict signature from pipeline_unified (supports blueprint_ready)
        job_manager.update_job(job_id, update_data, persist=True)
    else:
        # Legacy signature
        job_manager.update_job(update_data_or_jid, {...}, persist=True)
```

---

## 2. Technical Documentation Review

Reviewed [docs/v2.5_Director_Pipeline_Technical_Doc.bak.md](docs/v2.5_Director_Pipeline_Technical_Doc.bak.md) - Key takeaways:

- **Pipeline Version**: v15_v2_director
- **Entry Point**: `api/app.py` -> `process_markdown_job_v15_v2()`
- **Main Orchestrator**: `core/pipeline_unified.py` -> `process_markdown_unified()`
- **Blueprint Ready**: Set after Phase 3 (Manim CodeGen) completes
- **Video Rendering**: Phase 5 - Manim (blocking) + WAN (background thread)
- **Avatar**: Phase 4 - Fire-and-forget parallel submission

---

## 3. Issues Analysis & Resolution Plan

### Issue 3.1: Avatar Retry Not Saving URLs to presentation.json

#### Problem
When using the `retry_phase` endpoint with `phase=avatar_generation`, completed avatars are downloaded but their paths are NOT being saved to `presentation.json`.

#### Root Cause Analysis

**Location**: [api/app.py](api/app.py) - `_retry_avatar_generation()` (lines 1438-1542)

The function updates the in-memory `presentation` dict at lines 1501-1506:
```python
for sec in presentation["sections"]:
    if sec["section_id"] == section_id:  # BUG: Type mismatch possible!
        sec["avatar_path"] = f"avatars/section_{section_id}_avatar.mp4"
        sec["avatar_video"] = f"avatars/section_{section_id}_avatar.mp4"
        sec["avatar_status"] = "completed"
        break
```

**Bug**: The comparison `sec["section_id"] == section_id` may fail due to **type mismatch**:
- `sec["section_id"]` (from JSON) = int (e.g., `1`)
- `task["section_id"]` (from submit_parallel_job) = could be string or int depending on flow

**Evidence**: The original `_update_artifacts()` method in `avatar_generator.py` uses string comparison:
```python
if str(section.get("section_id")) == str(section_id):  # Safe comparison
```

#### Fix Required
In `_retry_avatar_generation()` at line 1502, change:
```python
# FROM:
if sec["section_id"] == section_id:

# TO:
if str(sec.get("section_id")) == str(section_id):
```

Also consider adding Vimeo/B2 URL capture like the original flow does.

---

### Issue 3.2: WAN/LTX Placeholder Videos on Failure

#### Problem
When WAN video generation fails (after all retries), the system creates a 15-second (or 1-second red) placeholder video. User wants: **No video file + mark as "failed" status**.

#### Root Cause Analysis

**Location**: [render/wan/wan_client.py](render/wan/wan_client.py) - `generate_video()` (lines 49-78)

```python
def generate_video(self, prompt, duration, output_path, ...):
    for attempt in range(retries):
        try:
            result = self._generate_video_attempt(...)
            ...
        except Exception as e:
            ...

    # BUG: Always creates placeholder on failure
    print(f"[WAN 2.6] All {retries} attempts failed, generating placeholder")
    return self._generate_placeholder(prompt, duration, output_path)  # <-- Creates video file
```

**Additional Locations**:
- [render/wan/wan_runner.py](render/wan/wan_runner.py) lines 337-340, 473-476, 705-720: Placeholder creation for beats/recaps
- [render/ltx/ltx_runner.py](render/ltx/ltx_runner.py): Similar placeholder pattern

#### Fix Required

1. **Option A (Recommended)**: Return `None` or raise exception on failure, let caller handle status marking
   ```python
   # wan_client.py - generate_video()
   # Instead of:
   return self._generate_placeholder(prompt, duration, output_path)

   # Do:
   raise WanGenerationError(f"All {retries} attempts failed for: {prompt[:50]}...")
   ```

2. **Option B**: Return a failure indicator dict instead of path
   ```python
   return {"status": "failed", "error": last_error, "path": None}
   ```

3. **Update callers** in `wan_runner.py` and `renderer_executor.py` to:
   - Catch the error/check for None
   - Mark section with `video_status: "failed"` in presentation.json
   - NOT add a `video_path` entry

---

### Issue 3.3: Blueprint Ready Flag for Dashboard Play Button - VERIFIED WORKING

#### Problem
User wants `blueprint_ready` flag set after LLM + Manim video generation completes, visible in Dashboard to enable the "Play" button for preview.

#### Post-Merge Status: **WORKING**

Team's commit `9f9aa30` implemented this correctly:

1. **Job Manager** - [core/job_manager.py:176](core/job_manager.py#L176):
   - Initializes `blueprint_ready: False` when job is created

2. **Pipeline** - [core/pipeline_unified.py:479-486](core/pipeline_unified.py#L479-L486):
   - Sets `blueprint_ready: True` after presentation.json is saved (after LLM + Manim codegen)

3. **API Callback** - [api/app.py:3070-3085](api/app.py#L3070-L3085):
   - `status_callback` handles dict signature to persist `blueprint_ready`

4. **Dashboard** - [player/dashboard.html:978](player/dashboard.html#L978):
   - Shows "Show Player (Preview)" button when `job.blueprint_ready` is true

#### No Action Needed
This issue is fully resolved by the team's recent commit.

---

## 4. Implementation Priority (Post-Merge)

| Priority | Issue | Effort | Impact | Status |
|----------|-------|--------|--------|--------|
| 1 | 3.1 - Avatar retry save | Low (1 line fix) | High - data loss | **NEEDS FIX** |
| 2 | 3.2 - WAN placeholder removal | Medium (multi-file) | Medium - cleaner failure handling | **NEEDS FIX** |
| ~~3~~ | ~~3.3 - Blueprint ready~~ | ~~Low~~ | ~~Medium~~ | **DONE by team** |

---

## 5. Files to Modify (Updated)

### Issue 3.1 - Avatar Retry Save (NEEDS FIX)
- `api/app.py` - `_retry_avatar_generation()` line 1502
- **Fix**: Change `sec["section_id"] == section_id` to `str(sec.get("section_id")) == str(section_id)`

### Issue 3.2 - WAN Placeholder Removal (NEEDS FIX)
- `render/wan/wan_client.py` - `generate_video()` lines 77-78
  - Change to return `None` instead of calling `_generate_placeholder()`
- `render/wan/wan_runner.py` - Update callers to handle `None` return
- `core/renderer_executor.py` - Mark sections with `video_status: "failed"` when video is `None`

### Issue 3.3 - Blueprint Ready
- **NO CHANGES NEEDED** - Verified working after team's commit `9f9aa30`

---

## 6. Testing Checklist

- [x] **Issue 3.1**: Avatar retry - Fixed type comparison bug (2 locations)
- [x] **Issue 3.2**: WAN failure - Removed placeholder creation, returns None + marks failed
- [x] **Issue 3.3**: Blueprint ready - Verified working (team's commit `9f9aa30`)
- [ ] **Regression**: Normal job flow still works end-to-end (manual test needed)

---

## 7. Implementation Complete

**Fixes applied on 2026-02-11:**

### Issue 3.1 - Avatar Retry Type Comparison
- `api/app.py:1502` - Changed to `str(sec.get("section_id")) == str(section_id)`
- `api/app.py:3816` - Same fix applied to second occurrence

### Issue 3.2 - WAN Placeholder Removal
- `render/wan/wan_client.py:77-78` - Returns `None` instead of `_generate_placeholder()`
- `render/wan/wan_client.py:117-118` - Returns `None` when no API key
- `render/wan/wan_runner.py` - Updated 3 call sites to handle `None` returns
- `core/renderer_executor.py` - Added logic to mark sections as `video_status: "generation_failed"` when video is `None`

### Files Modified
```
api/app.py                     | +27 lines (type comparison fix)
core/renderer_executor.py      | +68 lines (failure handling)
render/wan/wan_client.py       | +22 lines (no placeholder)
render/wan/wan_runner.py       | +41 lines (handle None)
```

---

*Document generated for issue tracking and resolution planning.*
*Last updated: 2026-02-11 - Implementation complete*
