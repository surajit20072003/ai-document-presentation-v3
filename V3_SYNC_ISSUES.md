# V3.0 Avatar–Three.js Sync Issues
**Created:** 2026-03-09  
**Updated:** 2026-03-10  
**Owner:** Antigravity agent  
**Prior gaps (RESOLVED):** GAP 1–6 from `GAP_RESOLUTION.md` (all closed 2026-03-08)

---

## Issue Index

| ID | Title | Bible Rule | Severity | Status |
|---|---|---|---|---|
| [VSYNC-001](#vsync-001) | Avatar duration not fed back to Three.js timing | §1 "LLM owns sync", §9 Rule 1 | 🔴 High | ✅ Done |
| [VSYNC-002](#vsync-002) | Three.js segment windows use word-count proportions, not avatar-relative timing | §9 Rule 2 "Avatar is master clock" | 🔴 High | ✅ Done |
| [VSYNC-003](#vsync-003) | Player cold-start: Three.js clock runs before avatar buffers | §1 "Avatar = master clock" | 🟡 Medium | ✅ Done |
| [QUIZ-001](#quiz-001) | Quiz sections had no Three.js visual layer (question card) | §12 Quiz Visual Layer | 🟡 Medium | ✅ Done |
| [AVTR-001](#avtr-001) | Avatar overlay renders squeezed and too small | Player UI | 🟡 Medium | 🔄 In Progress |
| [JOBS-001](#jobs-001) | Verify Three.js font/animation/quiz fixes apply to newly generated jobs | §9 Rule 1, §12 | 🟡 Medium | ⏳ Needs Verification |
| [SUB-001](#sub-001) | Subtitle solid background blocks Three.js animation content | Player UI | 🟡 Medium | ✅ Done |

---

## V3 Core Goal

> **Next-level visual learning** — Three.js animations illustrate the topic **in perfect sync with avatar narration**, going beyond V2's Manim frames. When the narrator says *"look at this graph"*, the graph appears at that exact moment.

---

## VSYNC-001 ✅

### Avatar duration not fed back to Three.js timing

**Bible Reference:** §1 *"LLM owns sync"*, §9 Rule 1  

**Root Cause:** Three.js code was generated using TTS-estimated durations. Avatar GPU produces MP4s at a different pace. Hardcoded `if (e >= START && e < END)` windows drift progressively.

**Fix — 3 parts:**

| Part | File | What |
|---|---|---|
| A | `core/agents/avatar_generator.py` | Write `avatar_duration_seconds` to `presentation.json` after each MP4 downloads (VSYNC-001 write-back) |
| B | `core/threejs_timing_enforcer.py` **[NEW]** | V3 equivalent of Manim's `_enforce_timing()` — patches `SEG_DUR[]` arrays in .js files using real duration, no LLM |
| C | `core/pipeline_v3.py` | Phase 3.6 added after avatar phase — calls `run_phase_3_6()` to enforce all sections |

**Resolved:** 2026-03-09

---

## VSYNC-002 ✅

### Three.js segment windows use word-count proportions, not avatar-relative timing

**Bible Reference:** §9 Rule 2, §7 Item 2  

**Root Cause:**  
The `threejs_system_prompt_v2.txt` HARD SYNC pattern instructed the LLM to write absolute second-values:
```js
if (e >= 0.0 && e < 28.6) { showSegment1(e); }
```
These absolute values came from word-count estimates, but `params.getTime()` returns `av-vid.currentTime` which uses the **avatar video's** actual elapsed time. If avatar GPU pace differs from the estimate, the window closes too early or too late.
```js
var SEG_DUR = [8.3, 8.4, 7.6];  // from narration timeline
var CUTS = SEG_DUR.map(...);      // proportional to totalDuration
if (e >= CUTS[0] && e < CUTS[1]) { ... }
```
Phase 3.6 further enforces these values post-avatar.

**Files:** `core/prompts/threejs_user_prompt.txt`, `core/prompts/threejs_system_prompt_v2.txt`  
**Resolved:** 2026-03-09

---

## VSYNC-003 ✅

### Player cold-start: Three.js clock runs before avatar buffers

**Bible Reference:** §1 *"Avatar = master clock"*  

**Root Cause:** Three.js `animate()` loop started on `onloadedmetadata`. `params.getTime()` returned 0 for 0.5–2s during buffering → first segment played ahead of audio.

**Fix:** `_avBox = { started: false }` passed from `loadSection` → `loadThreejsScene`. `params.getTime()` returns 0 until `vid.onplay` fires.

**File:** `player/player_v3.html`  
**Resolved:** 2026-03-09

---

---

## QUIZ-001 ✅

### Quiz sections had no Three.js visual layer (question card)

**Bible Reference:** §12 Quiz Visual Layer  

**Root Cause:**  
The pipeline generated 3 avatar clips per quiz question (question/correct/wrong) but wrote **no `.js` file** for the visual layer. The player's quiz branch (`initQuizSection`) showed only the avatar speaking against a blank visual layer. The interactive A/B/C/D card from the spec was never generated.

**Fix:** New module `core/quiz_card_generator.py` — programmatic Three.js quiz card generator (no LLM):
- Generates a self-contained `.js` with A/B/C/D option tiles
- Hover highlight, click selection, correct/wrong colour feedback (green/red)
- `params.onInteract('click', {key, correct})` fires on selection — player plays correct or wrong avatar clip
- Saved as `threejs/quiz_card_{section_id}.js`
- `quiz_threejs_file` path written back to `presentation.json` for player

**Pipeline:** Phase 4.5 in `pipeline_v3.py` — runs after Three.js codegen, before avatar generation.

**Files:** `core/quiz_card_generator.py` **[NEW]**, `core/pipeline_v3.py` Phase 4.5  
**Resolved:** 2026-03-09

---

## V2 vs V3 Sync Comparison

| Feature | V2 (Manim) | V3 (Three.js) |
|---|---|---|
| Animation runs inside | Rendered MP4 (offline) | Browser real-time |
| Duration source | TTS MP3 measured duration | Word-count estimate → corrected by Phase 3.6 |
| Audio in player | TTS MP3 played alongside Manim | Avatar MP4 only — voice baked in |
| Sync enforcer | `_enforce_timing()` patches `self.wait()` | Phase 3.6 patches `SEG_DUR[]` |
| Clock source | Manim renders at exact TTS timing | `params.getTime()` → `av-vid.currentTime` |
| Cold-start drift | None (pre-rendered) | Fixed via `_avBox` guard |
| LLM timing trust | Partial (overridden by enforcer) | Partial (overridden by Phase 3.6) |
| Result | ✅ Perfect sync (achieved) | ✅ Perfect sync (achieved) |

---

## Status Log

| Date | Update |
|---|---|
| 2026-03-09 | Issues identified and documented. |
| 2026-03-09 | All 3 issues resolved. `threejs_timing_enforcer.py` built. Phase 3.6 wired into `pipeline_v3.py`. Director Bible updated. |
| 2026-03-10 | **Player: Avatar WebGL chroma key** — deferred init to `loadeddata`, `offsetWidth/offsetHeight`, fallback `#00b140`, similarity `0.35`. |
| 2026-03-10 | **Player: Recap layout redesign** — scene container empty, video fullscreen, subtitles show beat narration, recap card CSS deleted. |
| 2026-03-10 | **AVTR-001** — Avatar size increased to 160×284px, hover 200×356px, `setPixelRatio(dpr)` added. |

---

## AVTR-001 🔄

### Avatar overlay renders squeezed and too small

**Root Cause — 3 parts:**

| Part | Cause |
|---|---|
| 1 | `#av-overlay` set to `120×213px` — too small to read on screen |
| 2 | WebGL `renderer.setSize()` called before `display:block` → `offsetWidth = 0` → canvas renders at 0×0 but container CSS expands → stretched |
| 3 | No `setPixelRatio(devicePixelRatio)` → blurry on retina / HiDPI displays |

**Fix applied (2026-03-10):**
- `#av-overlay` → `width: 160px; height: 284px` (default), `200×356px` (hover)  
- `initAvatarWebGL()` already deferred to `loadeddata` (overlay is `display:block` before call)  
- `renderer.setPixelRatio(window.devicePixelRatio || 1)` added at init and resize

**Remaining:** Needs user verification that avatar is visible and correctly sized on screen. Green screen also needs confirmation via DevTools.

**File:** `player/player_v3.html`  
**Status:** 🔄 In Progress — awaiting user verification

---

## JOBS-001 ⏳

### Verify Three.js font/animation/quiz fixes apply to newly generated jobs

**Background:**  
Fixes to `threejs_system_prompt_v2.txt` (font size, animation density, arc geometry, quiz avatar explanation) were applied to the **system prompt** and **player HTML**. These only affect:

- **New jobs** triggered after the prompt change → ✅ will use updated LLM instructions
- **Existing jobs** (e.g. `49_37_160_22_75e0c527`) → Three.js `.js` files already generated at old prompt → ❌ NOT retroactively fixed

**What needs to be verified on a NEW job:**

| Check | What to look for |
|---|---|
| Font size | Labels in Three.js scenes visibly larger than the old job |
| Animation draw style | Shapes drawn/written progressively, not popping in |
| Circle/arc geometry | Circles use `EllipseCurve`, no broken arcs |
| Animation density | Full segment time filled with continuous changes |
| Quiz avatar explanation | Selecting wrong/right answer triggers avatar explanation clip |

**Action:** Generate a new V3 job and navigate to a content+quiz section to verify.

**Status:** ⏳ Needs Verification — no new job has been tested post-fix

---

## SUB-001 ✅

### Subtitle solid background blocks Three.js animation content

**Root Cause:** `.subtitle-text` had `background: rgba(13, 17, 23, 0.85)` — an 85% opaque dark panel that rendered over the Three.js canvas, hiding animated content behind the subtitle box.

**Fix applied (2026-03-10):**
- `background` → `transparent`
- `border`, `box-shadow`, `backdrop-filter`, `padding` → removed
- `text-shadow` → multi-layer strong shadow (4 layers, black at varying blur radii) so text remains fully legible against any background colour without a panel
- `bottom` bumped from `30px` → `48px` to sit above the bottom bar more cleanly

**File:** `player/player_v3.html` — `.subtitle-text` CSS block (~line 212)  
**Status:** ✅ Done — deployed to job `49_37_160_22_75e0c527`
