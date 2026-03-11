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
| [AVTR-001](#avtr-001) | Avatar overlay renders squeezed and too small | Player UI | 🟡 Medium | ✅ Done |
| [JOBS-001](#jobs-001) | Verify Three.js font/animation/quiz fixes apply to newly generated jobs | §9 Rule 1, §12 | 🟡 Medium | ⏳ Needs Verification |
| [SUB-001](#sub-001) | Subtitle solid background blocks Three.js animation content | Player UI | 🟡 Medium | ✅ Done |
| [AVTR-002](#avtr-002) | Avatar completely invisible — WebGL canvas blank | Player UI | 🔴 High | ✅ Done |
| [AVTR-003](#avtr-003) | Avatar has box/border around it — should be frameless like a weatherman | Player UI | 🟡 Medium | ✅ Done |
| [AVTR-004](#avtr-004) | Avatar wrong size/position by section type | §13 Player Behaviour | 🔴 High | ✅ Done |
| [RECAP-001](#recap-001) | Recap beat videos not displaying full 15s — may be cut to 5s | §13 Player Behaviour | 🟡 Medium | ✅ Done |
| [THREEJS-001](#threejs-001) | Three.js scene code not rendering correctly in new job | §9 Rule 1 | 🔴 High | ✅ Done |
| [QUIZ-002](#quiz-002) | Quiz answers do not appear one-by-one while avatar reads; avatar missing from quiz | §12 Quiz Visual Layer | 🔴 High | ✅ Done |
| [UI-001](#ui-001) | Avatar squeezed (aspect ratio warped) + green screen from GLSL smoothstep bug | Player UI | 🟡 Medium | ✅ Done |
| [UI-002](#ui-002) | Playback button does not match V2 styling (lacks gradient/shadow) | Player UI | 🟢 Low | ✅ Done |
| [UI-003](#ui-003) | Global font sizes too small (titles, subtitles, buttons) | Player UI | 🟢 Low | ✅ Done |
| [DEV-001](#dev-001) | Need an in-browser Dev Mode overlay to adjust avatar size/position/transparency | Player UI | 🟢 Low | ✅ Done |

---

---

## AVTR-002 🔴 VALIDATED

### Avatar completely invisible — WebGL canvas blank

**Validated Root Cause (code confirmed):**  
`initAvatarWebGL()` is wrapped in a `loadeddata` event listener on `#av-vid` (line ~1157 in player_v3.html). But `#av-vid` has **no `src` at page load** — src is only set inside `loadSection()` when a section's avatar clip is assigned. The `loadeddata` event therefore never fires at startup, the WebGL renderer is never created, and the canvas stays blank for the entire session.

```javascript
// CURRENT (broken) — in initPlayer():
avVidEl.addEventListener('loadeddata', function () {
    initAvatarWebGL();   // ← never fires, av-vid has no src yet
}, { once: true });
```

**Final Resolution:**
1. Call `initAvatarWebGL()` **unconditionally** immediately after `document.getElementById('av-overlay').style.display = 'block'` in `initPlayer()` — no event guard.
2. Store the material reference: `avWebGL = { material, texture, renderer }` (already stored in `var avWebGL = null` at line 1048).
3. In `loadSection()` where `vid.src = avatarUrl` is set, after the first `vid.play()`, add a `loadeddata` listener **only for colour re-sampling**: read a pixel from the new frame and update `avWebGL.material.uniforms.keyColor.value`.
4. The renderer runs continuously via `requestAnimationFrame` — only the keyColor needs updating per clip.

**File:** `player/player_v3.html` — `initPlayer()` (~line 1145) and `loadSection()` (~line 1445)  
**Status:** 🔴 Validated — ready to implement

---

## AVTR-003 🟡 VALIDATED

### Avatar has visible box/border — should be frameless like a weatherman

**Validated Root Cause (code confirmed):**  
`#av-overlay` CSS at line 649–664 has:
```css
border-radius: 12px;
overflow: hidden;
box-shadow: 0 8px 32px rgba(0,0,0,.5);
border: 1px solid rgba(255,255,255,.1);
```
This creates a visible rounded card. The V2 reference `trig_v3_player.html` also had this box (lines 46–49) — it was the original design. The spec (`V3_requirements_updates.md` Layer Stack §Deliverable 3) says **"Always visible, weatherman mode"** — no box implied.

**Final Resolution:**
- Remove `border`, `box-shadow`, `border-radius`, `overflow:hidden` from `#av-overlay`.
- Add `background: transparent` to `#av-overlay`.
- Remove `#av-overlay .av-tag` name label (clutters borderless look).
- The `av-canvas` WebGL output with `alpha:true` is already transparent once chroma key is active — the container just needs to stop clipping it.

**File:** `player/player_v3.html` — `#av-overlay` CSS (~line 649)  
**Status:** 🟡 Validated — implement after AVTR-002 is working

---

## AVTR-004 🔴 VALIDATED

### Avatar wrong size/position — needs section-type-aware weatherman layout

**Validated Root Cause (code confirmed):**  
`#av-overlay` is hardcoded to `width:160px; height:284px; position:fixed; bottom:68px; right:16px` — the same size and position for every section type. The V2 trig reference player also used a fixed corner widget (100px). The **spec** (`V3_requirements_updates.md` §Deliverable 3, Layer Stack) says avatar is **"always visible, weatherman mode"**. The user has clarified the requirement:
- **Intro sections:** Avatar centred `80%` height, full bleed, no other content
- **All other sections:** Avatar right side, `60%` height, no box

**Final Resolution (exact implementation):**

1. **In `loadSection()`** — set a data attribute on `#av-overlay` when the section type is determined:
```javascript
var overlay = document.getElementById('av-overlay');
overlay.setAttribute('data-sectype', secType);
```

2. **In CSS** — replace the fixed-size block with section-type-aware rules:
```css
#av-overlay {
    position: fixed;
    z-index: 50;
    background: transparent;
    border: none;
    box-shadow: none;
    border-radius: 0;
    overflow: visible;
    display: none;
    transition: all .4s;
}
/* Intro: centred, tall */
#av-overlay[data-sectype="intro"] {
    bottom: 0;
    left: 50%;
    right: auto;
    transform: translateX(-50%);
    height: 80vh;
    width: auto;
}
/* All other sections: right side, 60% */
#av-overlay:not([data-sectype="intro"]) {
    bottom: 68px;
    right: 0;
    left: auto;
    transform: none;
    height: 60vh;
    width: auto;
}
```

3. **Canvas + video** — must inherit `height:100%; width:auto` to maintain 9:16 ratio.

4. **WebGL renderer** — must call `renderer.setSize(overlay.offsetWidth, overlay.offsetHeight)` **after** the section-type class is set (since overlay dimensions change).

**File:** `player/player_v3.html` — `#av-overlay` CSS + `loadSection()`  
**Bible:** §13 Player Behaviour table to be updated after implementation  
**Status:** 🔴 Validated — implement together with AVTR-002 + AVTR-003

---

## RECAP-001 🟡 VALIDATED

### Recap beat videos not displaying their full duration

**Validated Root Cause (code confirmed):**  
In `loadVideoScene()` (lines ~1591–1600), the beat advancement is driven by polling `av-vid.currentTime >= accumulatedTime`. The `accumulatedTime` is accumulated using `beatDurations[i]`, which comes from `narration.segments[i].duration_seconds` — the **narration audio duration**, NOT the WAN video file duration.

If a recap narration segment says `duration_seconds: 8` but its WAN video is `15s` long, the next beat is triggered at avatar time `8s` even though the 15s WAN video hasn't finished. The video is cut short.

V2 reference (`trig_v3_player.html`) used **pure staggered timeouts** for recap text reveals — it never had WAN video beat cycling. V3 introduced WAN beat videos for recap but wired them to narration time, not video time.

**Final Resolution:**

 In `loadVideoScene()`, for `section_type === 'recap'`, replace the `setInterval` avatar-clock poller with a `wanVid.onended` trigger:

```javascript
// CURRENT (avatar-clock drives beat advance — cuts recap video short):
var checkInterval = setInterval(function () {
    if (v && v.currentTime >= accumulatedTime) {
        clearInterval(checkInterval);
        playNextBeat();
    }
}, 50);

// FINAL (recap uses video natural end as advance trigger):
if (sec.section_type === 'recap' || sec.type === 'recap') {
    wanVid.onended = function () { playNextBeat(); };
} else {
    // non-recap: original avatar-clock poller
    var checkInterval = setInterval(function () {
        if (v && v.currentTime >= accumulatedTime) {
            clearInterval(checkInterval);
            playNextBeat();
        }
    }, 50);
}
```

**Prerequisite verification before applying:**  
Run `ffprobe -i <beat_video_path> -show_entries format=duration -v quiet` on a recap beat video to confirm actual file duration vs `narration.segments[i].duration_seconds` in `presentation.json`.

**File:** `player/player_v3.html` — `loadVideoScene()` beat loop  
**Status:** 🟡 Validated — verify actual video durations first, then apply

---

## THREEJS-001 ✅ DONE

### Three.js scenes not rendering correctly — SEG_DUR in milliseconds, not seconds

**Validated Root Cause (code confirmed):**  
The `avatar_generator.py` has two poll loops for HeyGen avatar status:
- **Primary loop** (line ~589): correctly converts `video_duration` ms→s with `if raw_duration > 1000: duration = raw_duration / 1000.0`
- **Secondary loop** (line ~934): **missing the division** — passed raw millisecond value directly to `_update_artifacts()`, storing e.g. `28839` (ms) as `avatar_duration_seconds: 28839.0` (falsely labelled seconds)

The timing enforcer then patched `SEG_DUR = [28839.0]` into each `.js` file, making every segment a ~8 hour window — animations fired only at the very start and never advanced.

**Fix applied (2026-03-10):**

1. **`core/agents/avatar_generator.py` line ~934** — added `if duration > 1000: duration = duration / 1000.0` guard to match the primary loop.

2. **Existing job `49_37_160_22_75e0c527`** — `presentation.json` patched (all 8 sections, ms→s). All 15 Three.js `.js` files had `SEG_DUR` rewritten from e.g. `[28839.0]` → `[28.839]` directly via the timing enforcer logic.

**Future jobs** will automatically store correct seconds via the patched code path.

**Files:** `core/agents/avatar_generator.py` (~line 934), 15 × `threejs/topic_*.js` in existing job  
**Status:** ✅ Done — 2026-03-10

---

## QUIZ-002 ✅ DONE

### Quiz answer options all appear at once — should reveal one by one while avatar reads

**Validated Root Cause (code confirmed):**  
`buildOptionButtons()` in `player_v3.html` (formerly lines 1984–2051) created all buttons in a `forEach` loop with no timing — all 4 appeared simultaneously when the avatar question clip ended.

The `quiz_card_generator.py` Three.js card has a `FADE_DUR = 0.8s` fade-in that also fires all 4 tiles at once via `scene.traverse()` + `opacity = fadeT`.

**Fix applied (2026-03-10) — player side:**
- All buttons start with `opacity: 0; transform: translateX(-12px)` (hidden, shifted left)
- `setTimeout` stagger: button 0 reveals at `0ms`, button 1 at `800ms`, button 2 at `1600ms`, button 3 at `2400ms`
- Each reveal transitions `opacity → 1` and `transform → translateX(0)` with `transition: all .35s` — slides in from left
- Stagger timers pushed to `timers[]` so `clearTimers()` on section change cleans them up

**Note on avatar during quiz:**  
`initQuizSection()` already calls `playQuizClip(clips.question, ...)` which sets `vid.src` — avatar IS playing during the question phase. The avatar overlay is not hidden in quiz, just shows the question clip. The staggered reveal now lines up with narration.

**File:** `player/player_v3.html` — `buildOptionButtons()` (~line 1984)  
**Status:** ✅ Done — 2026-03-10

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
| 2026-03-10 | **AVTR-002/003/004** ✅ — WebGL init moved unconditional; box removed; section-type CSS rules added. |
| 2026-03-10 | **UI-001** ✅ — WebGL aspect-ratio CONTAIN shader added; canvas auto-sizes to video native ratio on resize and per clip. |
| 2026-03-10 | **UI-001 GLSL bug** ✅ — `smoothstep` edge clamped to `max(smoothness, 0.001)` to prevent green screen from GPU undefined behaviour. |
| 2026-03-10 | **UI-002** ✅ — Confirmed V2 `.pb` gradient/shadow CSS already applied; no change needed. |
| 2026-03-10 | **UI-003** ✅ — Font sizes increased: intro-title 64px, sum-hd 32px, sbullet-t 18px (font-weight 500), subtitle-text 24px. |
| 2026-03-10 | **DEV-001** ✅ — Dev Mode overlay (Shift+D) added with sliders for similarity, smoothness, height, Three.js scale, raw video toggle. |
| 2026-03-10 | **AVTR-004** ✅ — `loadSection()` now writes `data-sectype` attribute on `#av-overlay`; intro CSS centring is now active. |
| 2026-03-10 | **MOBILE** ✅ — Tap-to-start overlay, AudioContext unlock on touchstart, and setInterval stall checkers for av-vid and wan-vid. |

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

---

## UI-001 ✅ (Avatar Aspect Ratio + Green Screen)

### Avatar squeezed and/or green screen visible

**Root Cause — 2 parts:**

| Part | Cause |
|---|---|
| 1 | WebGL canvas forced to fixed 9:16 CSS box — video UV not aspect-corrected in shader |
| 2 | `smoothstep(x, x, blend)` with `smoothness=0.0` is GLSL undefined → GPU returns 1.0 → fully opaque green screen |

**Fix applied (2026-03-11):**
- Fragment shader uses `uCanvasAspect` and `uVideoAspect` uniforms to implement `object-fit: contain` UV correction — avatar shows full-width without squeezing
- `resize` listener dynamically sets `#av-overlay` width = `h × videoAspect` so container exactly matches video natural ratio
- `loadeddata` dispatches a resize event per clip so new clip dimensions are picked up immediately  
- GLSL: `smoothstep(similarity, similarity + max(smoothness, 0.001), blend)` — `max()` prevents equal-edge undefined behaviour

**File:** `player/player_v3.html` — shader uniforms + resize listener  
**Status:** ✅ Done — 2026-03-11

---

## UI-002 ✅ (Playback Button)

### Playback button matches V2 styling

**Resolution:** Confirmed that the `.pb` CSS in `player_v3.html` already has `linear-gradient(135deg, var(--gold), var(--amber))` and `box-shadow: 0 4px 16px rgba(246,196,78,.25)` matching V2. No code change required.  
**Status:** ✅ Done — confirmed 2026-03-10

---

## UI-003 ✅ (Global Font Size)

### Global font sizes increased

**Fix applied (2026-03-10):**
- `.subtitle-text` → 24px
- `.intro-title` → 64px  
- `.sum-hd` → 32px
- `.sbullet-t` → 18px, `font-weight: 500` (typo `50` corrected 2026-03-11)

**File:** `player/player_v3.html`  
**Status:** ✅ Done — 2026-03-11

---

## DEV-001 ✅ (Dev Mode)

### In-browser Dev Mode overlay implemented

**Fix applied (2026-03-10):**
1. `<div id="dev-overlay">` injected into `#app` — hidden by default
2. Keyboard shortcut **Shift + D** toggles the overlay
3. Sliders wired to live `avWebGL.material.uniforms`:
   - **Similarity** (0–1) — chroma key threshold
   - **Smoothness** (0–1) — edge softness
   - **Intro Height vh** (30–100) — avatar height on intro sections
   - **Content Height vh** (20–100) — avatar height on other sections
   - **Three.js Scale** (0.5–2.0) — scales `#threejs-layer` via CSS transform
4. **Show Raw AV Video** checkbox — bypasses WebGL, shows original green-screen video for debugging

**File:** `player/player_v3.html`  
**Status:** ✅ Done — 2026-03-10
