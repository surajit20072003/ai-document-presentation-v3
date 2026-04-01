# Memory Infographic Wiring — Implementation Plan
**Date**: 2026-03-31  
**Status**: Ready for Implementation  
**Prerequisites**: Steps 1A-1C (prompt changes), Step 2A (enhancer code), Step 3A-3C (tests) are ALREADY COMPLETE.

---

## Problem

The Global Director prompt already outputs a `memory_infographic` section (added in Step 1C), but it gets **silently dropped** during pipeline stitching. Two reasons:

1. **Stitching code** (`partition_director_generator.py:364`) only extracts `["memory", "recap"]` keys from Global Director output
2. **Prompt schema** uses `infographics[]` format, but the existing infographic renderer expects `render_spec.infographic_beats[]`

---

## Changes Required (5 files)

### Change 1: Global Director Prompt Schema (prompt file only)

**File**: `core/prompts/director_global_prompt.txt`  
**Lines**: 287-314 (the Schema block within MEMORY INFOGRAPHIC SECTION)

**Current schema** (broken — uses custom `infographics[]` format):
```json
{
  "section_type": "memory_infographic",
  "renderer": "infographic",
  "infographics": [
    {
      "infographic_id": "inf_1",
      "image_prompt": "...",
      "narration": { "segment_id": "...", "text": "..." }
    }
  ]
}
```

**New schema** (matches existing `image_to_video` section pattern):
```json
{
  "section_type": "memory_infographic",
  "renderer": "infographic",
  "text_layer": "hide",
  "visual_layer": "show",
  "avatar_layer": "show",
  "render_spec": {
    "infographic_beats": [
      {
        "beat_id": "inf_1",
        "image_prompt": "100+ words. Static infographic. Style: Scientific Process Diagram. Dark background #0d1117. 16:9. No watermarks. Publication quality.",
        "start_seconds": 0.0,
        "end_seconds": 15.0
      }
    ]
  },
  "narration": {
    "segments": [
      {
        "segment_id": "inf_seg_1",
        "text": "Avatar narration explaining what the student sees.",
        "pace": "slow",
        "pause_after_seconds": 1.0,
        "gesture": null,
        "purpose": "explain",
        "duration_seconds": 15.0,
        "start_seconds": 0.0,
        "end_seconds": 15.0
      }
    ],
    "total_duration_seconds": 45.0
  }
}
```

**What changes in the prompt text**:
- Replace `infographics[]` array with `render_spec.infographic_beats[]`
- Move `narration` from inside each infographic to section-level `narration.segments[]` (matching how content sections work)
- Add `text_layer`, `visual_layer`, `avatar_layer` display directives at section level
- Keep `style_name` and `style_reason` fields inside each beat (for LLM quality guidance)
- Update SELF-CHECK to match new structure

---

### Change 2: Pipeline Stitching Code

**File**: `core/partition_director_generator.py`  
**Line**: 364

**Current**:
```python
# 4. Memory and Recap (Global Footer)
for key in ["memory", "recap"]:
```

**New**:
```python
# 4. Memory, Memory Infographic, and Recap (Global Footer)
for key in ["memory", "memory_infographic", "recap"]:
```

**Effect**: The Global Director's `memory_infographic` output gets extracted and appended between Memory and Recap in the section order.

---

### Change 3: Renderer Policy

**File**: `core/renderer_executor.py`  
**Lines**: 167-172 (after the manim/threejs passthrough)

**Add after line 172**:
```python
# V3: 'infographic' is valid for memory_infographic — never override
elif current_renderer == "infographic" and section_type == "memory_infographic":
    pass  # Allow infographic renderer through unchanged
```

**Why**: The current policy only allows `manim`/`threejs` for `content`/`example` sections. Without this, the infographic renderer for `memory_infographic` could be incorrectly overridden.

Note: `memory_infographic` is NOT in `TEXT_ONLY_SECTION_TYPES` (line 30), so it won't be forced to `"none"`.

---

### Change 4: Pipeline Phase 6.5 — Infographic Image Generation

**File**: `core/pipeline_v3.py`  
**Insert after line 969** (after the V3 video generation save block, before per_question handling)

**Add**:
```python
# V3: Handle infographic sections (memory_infographic, etc.) via execute_renderer()
infographic_sections = [
    s for s in presentation.get("sections", [])
    if s.get("renderer") == "infographic"
]
if infographic_sections and not skip_wan:
    log(
        "infographic",
        f"Starting infographic generation for {len(infographic_sections)} section(s)...",
    )
    try:
        from core.renderer_executor import execute_renderer

        for section in infographic_sections:
            section_id = section.get("section_id", "?")
            log("infographic", f"  Processing infographic section {section_id}...")

            result = execute_renderer(
                topic=section,
                output_dir=str(output_path / "images"),
                dry_run=dry_run,
                skip_wan=skip_wan,
                video_provider=video_provider,
            )

            if result.get("status") == "success":
                log("infographic", f"    ✅ Section {section_id} complete")
            else:
                log("infographic", f"    ❌ Section {section_id} failed: {result.get('error', 'Unknown error')}")

        log("infographic", f"✅ Infographic generation complete for {len(infographic_sections)} section(s).")
    except Exception as e:
        logger.warning(f"[V3] Infographic generation error (non-fatal): {e}")
        log("infographic", f"⚠️ Infographic error (non-fatal): {e}")

    # Save presentation.json with image paths
    try:
        with open(pres_path, "w", encoding="utf-8") as f:
            json.dump(presentation, f, indent=2, ensure_ascii=False)
        log("infographic", "✅ presentation.json saved with infographic image paths.")
    except Exception as e:
        logger.warning(f"[V3] Failed to save presentation.json after infographic gen: {e}")
```

**How it works**:
- `execute_renderer()` at `renderer_executor.py:1138` already handles `renderer: "infographic"`
- It reads `render_spec.infographic_beats[]`, calls `generate_image_for_beat()` for each
- Gemini generates PNGs → saves to `jobs/{id}/images/{id}_{beat_id}.png`
- Updates `spec["image_path"]` with relative path
- The existing infographic handler also merges these into the schedule via `infos` at `player_v3.html:2646`

---

### Change 5: Player Routing

**File**: `player/player_v3.html`

#### 5a. Badge Map (line 1657)

**Current**:
```javascript
var BADGE_MAP = {
    intro: { label: 'INTRO', cls: 'badge-intro' },
    summary: { label: 'SUMMARY', cls: 'badge-summary' },
    content: { label: 'CONTENT', cls: 'badge-content' },
    example: { label: 'EXAMPLE', cls: 'badge-example' },
    memory: { label: 'MEMORY', cls: 'badge-memory' },
    recap: { label: 'RECAP', cls: 'badge-recap' },
    quiz: { label: 'QUIZ', cls: 'badge-quiz' },
};
```

**Add** after `memory` line:
```javascript
memory_infographic: { label: 'MEMORY VISUAL', cls: 'badge-memory' },
```

#### 5b. Section Type Routing — onloadedmetadata (line 2357-2359)

**Current**:
```javascript
} else if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    sec.section_type === 'recap') {
```

**Add** `sec.section_type === 'memory_infographic' ||` to the condition:
```javascript
} else if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    sec.section_type === 'recap' ||
    sec.section_type === 'memory_infographic') {
```

#### 5c. Section Type Routing — durationchange (line 2371-2373)

**Current**:
```javascript
if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    capturedSec.section_type === 'recap') {
```

**Add** `capturedSec.section_type === 'memory_infographic' ||`:
```javascript
if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    capturedSec.section_type === 'recap' ||
    capturedSec.section_type === 'memory_infographic') {
```

#### 5d. Section Type Routing — fallback (line 2443-2445)

**Current**:
```javascript
} else if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    sec.section_type === 'recap') {
```

**Add** `sec.section_type === 'memory_infographic' ||`:
```javascript
} else if (renderer === 'video' || renderer === 'wan_video' ||
    renderer === 'text_to_video' || renderer === 'image_to_video' ||
    sec.section_type === 'recap' ||
    sec.section_type === 'memory_infographic') {
```

#### 5e. Section Init Hook (line 2456)

**Add after line 2456**:
```javascript
if (secType2 === 'memory_infographic') initMemoryInfographicSection(sec, idx);
```

The `initMemoryInfographicSection()` function can be a simple no-op initially (like `initRecapSection`), since the visual display is handled entirely by `loadVideoScene()` which already supports `infographic_beats`.

**Why this works**: `loadVideoScene()` at line 2646 already reads `rs.infographic_beats` and merges them into the visual schedule. The player already knows how to display static images synced to narration timing. We just need to route `memory_infographic` sections to use `loadVideoScene()` instead of falling through.

---

## Execution Order

```
1. Update Global Director prompt schema (director_global_prompt.txt)
   → Replace infographics[] with render_spec.infographic_beats[]
   → Flatten narration to section-level segments[]

2. Fix stitching code (partition_director_generator.py:364)
   → Add "memory_infographic" to extraction keys

3. Fix renderer policy (renderer_executor.py:167-172)
   → Allow infographic renderer for memory_infographic

4. Add infographic to pipeline Phase 6.5 (pipeline_v3.py:969+)
   → Collect infographic sections, call execute_renderer()

5. Add player routing (player_v3.html)
   → Badge map (5a), 3x routing checks (5b-5d), init hook (5e)

6. Dry run test
   → Run new job with updated prompts
   → Run test_director_schema.py → verify memory_infographic present
   → Run test_tts_pace_pause.py → verify all segments pass
   → Verify images/ directory has generated PNGs
```

---

## Verification Checklist

| Check | How to Verify |
|-------|--------------|
| memory_infographic section in presentation.json | `test_director_schema.py` — no "MISSING" error |
| render_spec.infographic_beats[] present | Inspect section structure in JSON |
| narration.segments[] with pace/pause/gesture | `test_tts_pace_pause.py` — all PASS |
| Images generated in jobs/{id}/images/ | Check directory after pipeline run |
| Image paths written to infographic_beats | Check `image_source` field in beats |
| Player displays infographics synced to narration | Manual player test |
| Badge shows "MEMORY VISUAL" | Visual check in player |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LLM doesn't follow new schema | Prompt has explicit schema + SELF-CHECK. If needed, add JSON schema validation in `_run_global_worker()` |
| Infographic images fail to generate | `execute_renderer()` is non-fatal — pipeline continues with missing images |
| Player doesn't sync timing | `loadVideoScene()` already handles `infographic_beats` — minimal risk |
| Narration timing mismatch with image display | Each beat has `start_seconds`/`end_seconds` matching narration segment timing |
