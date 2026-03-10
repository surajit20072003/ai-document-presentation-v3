# V3 Gap Resolution Package
**Date:** 2026-03-08  
**For:** Antigravity agent — apply these changes in order  
**Status as of 2026-03-08:** ✅ ALL GAPS RESOLVED

---

## Summary

| Gap | Fix | File(s) changed | Status |
|---|---|---|---|
| GAP 1 | `fill_prompt_v2.py` — logic is embedded, spec updated to reflect | `requirements_build_for_v3.md` (1 line) | ✅ Done |
| GAP 2 | Add interaction taxonomy + `interaction` field to Director prompt | `director_v3_partition_prompt.txt` | ✅ Done 2026-03-08 |
| GAP 3 | Wire pointer events in player | `player_v3.html` | ✅ Done 2026-03-08 |
| GAP 4 | Interaction hint UI (B5) | `player_v3.html` | ✅ Done 2026-03-08 |
| GAP 5 | Rename/copy system prompt to match spec | `threejs_system_prompt_v2.txt` created; `threejs_code_generator.py` updated | ✅ Done 2026-03-08 |
| GAP 6 | Add 4 interaction rules to validator | `v3_validator.py` | ✅ Done 2026-03-08 |

---

## GAP 1 — `fill_prompt_v2.py` (docs only) ✅ RESOLVED

The functionality is correctly embedded in `threejs_code_generator._build_user_prompt()`.  
**Action:** In `requirements_build_for_v3.md`, change the deliverables table row:

```
| `fill_prompt_v2.py` | Prompt builder ... | ✅ Built 2026-03-08 |
```
→
```
| `fill_prompt_v2.py` | Prompt builder — logic embedded in `threejs_code_generator._build_user_prompt()` | ✅ Embedded |
```

No code change needed.

---

## GAP 2 — Director prompt: add interaction taxonomy ✅ RESOLVED

**File changed:** `core/prompts/director_v3_partition_prompt.txt`

**Changes made (2026-03-08):**
1. Added `"interaction": null` to the first `segment_spec` example in the JSON schema
2. Added a second `segment_spec` example showing a non-null `interaction` object (`drag_point`)
3. Appended the full `=== INTERACTION RULES (MANDATORY) ===` block before the final output instruction, including:
   - 5 allowed types with descriptions
   - Decision rules by complexity
   - NEVER conditions
   - Interaction object schema
   - `threejs_spec` writing guide per interaction type

---

## GAP 3 — Player pointer-event wiring ✅ RESOLVED

**File changed:** `player/player_v3.html`

**Changes made (2026-03-08):**
- After `activeScene = sceneFn(...)` (line ~1277), injected the full pointer-event wiring block:
  - `_getPointerNorm(e)` — normalises mouse/touch to [0,1] coords
  - `_dispatchMove/Down/Up` — forward to `activeScene.onPointerMove/Down/Up`
  - Listeners added only when scene declares pointer hooks
  - `threejsLayer._pointerCleanup` stored for teardown
  - Interaction timeout (`setTimeout` → `loadSection(curSec+1)`)
  - `params.onInteract` wrapped to clear timer on first interaction
- In `loadSection` teardown (line ~1148), added:
  - Call to `threejsLayer._pointerCleanup()` before clearing the layer innerHTML

---

## GAP 4 — Interaction hint UI (B5) ✅ RESOLVED

**File changed:** `player/player_v3.html`

**Changes made (2026-03-08):**
- After the pointer wiring block, added hint-display logic using `document.getElementById('interaction-hint')`
- Hint text map: `hover_highlight → "👆 Hover over the objects"`, `drag_point → "✋ Drag the point"`, etc.
- Hint fades in at opacity 1 then fades out after 3000ms
- Added the `<div id="interaction-hint">` element to the HTML body (before `#av-overlay`), styled with gold Caveat font, pill-shaped, position:fixed bottom:80px, z-index:55

---

## GAP 5 — System prompt filename ✅ RESOLVED

**Actions taken (2026-03-08):**
1. `cp core/prompts/threejs_system_prompt.txt core/prompts/threejs_system_prompt_v2.txt`
2. In `core/agents/threejs_code_generator.py > _load_prompts()`: now checks for `threejs_system_prompt_v2.txt` first, falls back to `threejs_system_prompt.txt` if not found. Original file kept for rollback.

---

## GAP 6 — Validator: add interaction rules ✅ RESOLVED

**File changed:** `core/v3_validator.py`

**Changes made (2026-03-08):**
- Added constants:
  - `VALID_INTERACTION_TYPES = {'hover_highlight', 'click_reveal', 'drag_point', 'rotate_inspect', 'slider'}`
  - `INTERACTION_MIN_DURATION = 8.0`
- Added `_check_interaction_rules(section)` function enforcing:
  1. `interaction` key must be present on every `segment_spec` (null is valid)
  2. `interaction.type` must be one of 5 defined types
  3. Non-null interaction + `segment_duration_seconds < 8.0` → error
  4. `type='slider'` + `complexity='simple' or 'medium'` → error
  5. Non-null interaction missing `timeout_seconds` → error
- Added `_check_interaction_rules` call inside `validate_section_v3()` after `_check_threejs_spec()`

---

## Apply Order (completed)

```
1. GAP 5  ✅ — rename prompt file (no logic change, do first)
2. GAP 2  ✅ — update director prompt (adds interaction field to all future outputs)
3. GAP 6  ✅ — update validator (will now catch missing interaction fields)
4. GAP 3  ✅ — update player (pointer wiring + interaction timeout)
5. GAP 4  ✅ — update player (hint UI HTML element + display logic)
6. GAP 1  ✅ — topic_reference_scene.js already existed; GAP 1 is docs-only note
```
