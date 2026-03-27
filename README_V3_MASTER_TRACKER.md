# V3 — Master Issue Tracker
**Project**: AI Document Presentation V3  
**Last Updated**: 2026-03-25  
**Purpose**: Single source of truth — every issue, fix, and implementation status

---

## Status Key
- ✅ Implemented & Verified
- 🔶 Implemented — needs verification
- 🔴 Not implemented
- ⚠️ Partially implemented — follow-up needed

---

## PIPELINE ISSUES

---

### IMG-002 — Image 404 / Absolute Path in presentation.json
**Files**: `pipeline_v3.py`, `image_generator.py`  
**Status**: ✅ Implemented & Verified

**Problem**  
`image_generator.py` returns full absolute disk paths (e.g. `/nvme0n1-disk/.../images/photo.png`) into `presentation.json`. Browser cannot resolve these — results in 404 and blank screen.  
Two root causes:
1. `pipeline_v3.py` Phase 1.5 path normalization gated behind `if saved_images:` — skipped when no PDF images present
2. `image_generator.py` `generate_image_for_beat()` returns absolute path instead of relative

**Fix**  
`pipeline_v3.py` — Remove `if saved_images:` gate; update `_fix_image_source()` to strip absolute prefix using `os.path.basename` and scan both `images/` and `generated_images/` for stem match.  
`image_generator.py` — Capture absolute path from `gen.generate_image()`, return `os.path.join('images', os.path.basename(abs_path))`.  
Note: extension may differ from `.png` if Gemini returns JPEG/WEBP — always use `os.path.basename(abs_path)` not a hardcoded filename.

**Verification**  
- [x] Run job without PDF images
- [x] Open `presentation.json` — all `image_source` values must be `images/filename.ext` or `generated_images/filename.ext`
- [x] No `/nvme`, `/home`, or absolute path segments anywhere
- [x] No 404 errors in browser console for image files

---

### SUBST-001 — `{{subject}}` / `{{grade}}` Spoken Verbatim by Avatar
**File**: `pipeline_v3.py` (stitcher / pre-avatar phase)  
**Status**: ✅ Implemented & Verified

**Problem**  
Global Director prompt uses `{{subject}}` and `{{grade}}` as placeholders. Avatar is generated before substitution runs — TTS speaks the literal strings `{{subject}}` and `{{grade}}` to the student.

**Fix**  
Add `substitute_placeholders()` function in `pipeline_v3.py`. Invoke it after Phase 1/2.5 (Director output parsed) but BEFORE Phase 3.3 (Avatar Generation). Function recursively replaces all string values in the presentation data dict.

```python
def substitute_placeholders(presentation_data: dict, subject: str, grade: str) -> dict:
    replacements = {'{{subject}}': subject, '{{grade}}': str(grade)}
    def replace_in_value(val):
        if isinstance(val, str):
            for k, v in replacements.items(): val = val.replace(k, v)
            return val
        elif isinstance(val, dict): return {k: replace_in_value(v) for k, v in val.items()}
        elif isinstance(val, list): return [replace_in_value(i) for i in val]
        return val
    return replace_in_value(presentation_data)
```

**Verification**  
- [x] Run job with subject="Biology", grade="10" (or in this case, "Pharma", "1")
- [x] Intro `narration.full_text` in `presentation.json` reads properly translated text
- [x] Avatar MP4 audio speaks the true subject and grade — not placeholder text

---

### INDENT-001 — IndentationError in pipeline_v3.py line 181
**File**: `pipeline_v3.py`  
**Status**: ✅ Implemented & Verified

**Problem**  
After removing the `if saved_images:` gate (IMG-002), the Phase 1.5 block was left with 8-space indent instead of 4-space. Python throws `IndentationError: unexpected indent` at line 181.

**Fix**  
De-indent lines 181–240 by 4 spaces. Run `python3 -m py_compile core/pipeline_v3.py` to confirm clean.

**Verification**  
- [x] `python3 -m py_compile core/pipeline_v3.py` returns no errors
- [x] Application imports cleanly on restart

---

## PLAYER ISSUES — `player_v3.html`

---

### SUMM-01 — Summary Bullets Use Wall-Clock Timer, Not Avatar Clock
**Function**: `initSummarySection` (~line 2387)  
**Status**: ✅ Implemented & Verified

**Problem**  
Bullets reveal at hardcoded `setTimeout(400 + i * 1800)` — every 1.8 seconds regardless of avatar speed. Completely disconnected from narration. Narration segments already have `start_seconds` — player ignores them.

**Fix**  
Replace entire `initSummarySection` with `timeupdate` listener that checks `seg.start_seconds`:

```js
function initSummarySection(sec) {
    if (!sec.narration || !sec.narration.segments) return;
    var segments = sec.narration.segments;
    var sectionAtLoad = curSec;
    var avEl = document.getElementById('av-vid');
    segments.forEach(function (_, i) {
        var el = document.getElementById('sb-' + sec.section_id + '-' + i);
        if (el) el.classList.remove('show');
    });
    function onTimeUpdate() {
        if (curSec !== sectionAtLoad) { avEl.removeEventListener('timeupdate', onTimeUpdate); return; }
        var t = avEl.currentTime;
        segments.forEach(function (seg, i) {
            var threshold = (seg.start_seconds !== undefined) ? seg.start_seconds : (i * 5);
            if (t >= threshold) {
                var el = document.getElementById('sb-' + sec.section_id + '-' + i);
                if (el && !el.classList.contains('show')) el.classList.add('show');
            }
        });
    }
    avEl.addEventListener('timeupdate', onTimeUpdate);
}
```

**Verification**  
- [x] Summary section plays — bullets appear exactly when avatar speaks each objective
- [x] Pause avatar mid-summary — bullets stop appearing
- [x] Resume — bullets continue from correct point

---

### SUMM-02 — Intro Sentence Shows as Bullet #0
**Function**: `buildSummaryHTML` (~line 1498)  
**Status**: ✅ Implemented & Verified

**Problem**  
First segment (`purpose: "introduce"`) — "Here are the key learning objectives…" — is rendered as numbered bullet #1 alongside actual objectives. Should not appear as a bullet.

**Fix**  
Filter `purpose: "introduce"` segments before building bullets. Use `origIdx` (position in full array) for DOM id so `initSummarySection` timeupdate listener can still find elements by segment position. MUST be applied together with SUMM-01.

```js
function buildSummaryHTML(sec) {
    var allSegments = (sec.narration && sec.narration.segments) ? sec.narration.segments : [];
    var bulletSegments = allSegments.filter(function (seg) { return seg.purpose !== 'introduce'; });
    var items = bulletSegments.slice(0, 6).map(function (seg, i) {
        var origIdx = allSegments.indexOf(seg);
        return '<div class="sbullet" id="sb-' + sec.section_id + '-' + origIdx + '">' +
            '<div class="sbullet-n">' + (i + 1) + '</div>' +
            '<div class="sbullet-t">' + esc((seg.text || '').substring(0, 120)) + '</div></div>';
    }).join('');
    return '<div style="align-items:flex-start;max-width:680px;margin:0 auto;width:100%;display:flex;flex-direction:column;gap:10px">' +
        '<div class="sum-hd">By the end of this section, you will...</div>' + items + '</div>';
}
```

**Verification**  
- [x] Summary section shows only actual objectives (not the intro sentence) as numbered bullets
- [x] Bullet count matches number of `purpose: "explain"` segments

---

### QUIZ-HIDE — Question Card Visible During Explanation Video
**Functions**: `showExplanationVisual` (~line 2592), `onAnswer` setTimeout (~line 2743)  
**Status**: ✅ Implemented & Verified

**Problem**  
After student answers, explanation video plays but quiz card and options are still visible (dimmed but present). Card and options should be completely hidden so video plays full screen.  
Additional: overlay background `rgba(13,17,23,0.15)` still tints the video dark.

**Final correct fix**

In `showExplanationVisual`:
```js
// Hide card and options entirely
var card = document.getElementById('quiz-question-card');
var opts = document.getElementById('quiz-options');
if (card) card.style.display = 'none';
if (opts) opts.style.display = 'none';
// Fully transparent overlay — video shows unobscured
document.getElementById('quiz-overlay').style.background = 'transparent';
```

In `onAnswer` setTimeout restore:
```js
document.getElementById('quiz-overlay').style.background = 'rgba(13,17,23,0.96)';
var card = document.getElementById('quiz-question-card');
var opts = document.getElementById('quiz-options');
if (card) { card.style.display = 'block'; card.style.background = '#161b22'; }
if (opts) { opts.style.display = 'grid'; opts.style.opacity = '1'; }
// CRITICAL: opts must restore to display:'grid' not display:'block'
```

**Verification**  
- [x] Answer question → card and options completely disappear
- [x] Explanation video plays full screen with zero dark tint
- [x] ✅/❌ feedback strip and QUIZ-NAV buttons remain visible
- [x] Card and options restore cleanly for next question

---

### SUB-DRIFT — Karaoke Subtitle Drifts After Video Stall
**Function**: `renderSubtitleKaraoke` (~line 1879)  
**Status**: ✅ Implemented & Verified

**Problem**  
Fixed `wordDurMs` interval calculated once at segment start. After any buffer stall, words advance ahead of speech. No recovery — drift persists for entire segment.

**Fix**  
Replace fixed interval counter with `av-vid.currentTime`-anchored word index. Dev implemented at 50ms (better than spec's 100ms):

```js
var segStartTime = null;
var currentWord = 0;
_karaokeTimer = setInterval(function () {
    if (curSec !== sectionAtLoad) { clearInterval(_karaokeTimer); _karaokeTimer = null; return; }
    var avEl2 = document.getElementById('av-vid');
    if (!avEl2 || avEl2.paused) return;
    if (segStartTime === null) segStartTime = avEl2.currentTime;
    var elapsed = avEl2.currentTime - segStartTime;
    var targetWord = Math.min(Math.floor((elapsed / beatDur) * words.length), words.length - 1);
    if (targetWord > currentWord) {
        for (var w = currentWord; w < targetWord; w++) {
            var el = document.getElementById('kw-' + w);
            if (el) el.className = 'sub-word spoken';
        }
        currentWord = targetWord;
        var activeEl = document.getElementById('kw-' + currentWord);
        if (activeEl) activeEl.className = 'sub-word active';
    }
    if (currentWord >= words.length - 1) { clearInterval(_karaokeTimer); _karaokeTimer = null; }
}, 50);
```

**Verification**  
- [x] Play content section — pause for 5 seconds — resume
- [x] Subtitle resumes from correct word position (no jump, no rush)
- [x] Words stay in sync with speech throughout entire segment

---

### SUB-QUIZ — Stale / Wrong Subtitles During Quiz
**Functions**: `initQuizSection` (~line 2556), `playClip` (~line 2579)  
**Status**: ✅ Implemented & Verified

**Problem — Two paths**  
Path A (dedicated quiz section): `startSubtitleDriver` never called — no subtitles  
Path B (inline understanding_quiz): Content section karaoke timer keeps running — stale content narration scrolls during quiz (confirmed in screenshot: "When similar cells group together…")

**Fix — Step 1: Kill stale subtitle on quiz entry**  
At very start of `initQuizSection`:
```js
function initQuizSection(sec) {
    if (_karaokeTimer) { clearInterval(_karaokeTimer); _karaokeTimer = null; }
    document.getElementById('subtitle-overlay').style.display = 'none'; // ← CRITICAL LINE
    // ... rest of existing code
```

**Fix — Step 2: Show subtitles during quiz clips**  
Update `playClip` to accept `scriptText` param:
```js
function playClip(url, onEnd, scriptText) {
    vid.onended = null;
    var subEl = document.getElementById('subtitle-overlay');
    var subTextEl = document.getElementById('subtitle-text');
    if (url) {
        vid.src = getMediaSrc(url); vid.load(); vid.play().catch(function () { });
        if (scriptText && subEl && subTextEl) {
            subTextEl.className = 'subtitle-text';
            subTextEl.innerHTML = esc(scriptText);
            subEl.style.display = 'block';
        }
        vid.onended = function () {
            if (subEl) subEl.style.display = 'none';
            if (onEnd) onEnd();
        };
    } else {
        if (subEl) subEl.style.display = 'none';
        timers.push(setTimeout(onEnd || function () { }, 2000));
    }
}
```

**Fix — Step 3: Pass scripts at call sites**  
```js
// Question clip
playClip(clips.question, function () { revealAllButtons(); }, narr.question_script || '');

// Explanation clip
playClip(clips.explanation, function () { ... }, narr.explanation_script || '');
```

**Verification**  
- [x] Navigate to quiz section — NO content narration subtitle visible at bottom
- [x] Question clip plays — question narration text appears as subtitle
- [x] Explanation clip plays — explanation narration text appears as subtitle
- [x] Subtitle disappears cleanly when each clip ends

---

### QUIZ-NAV — No Navigation Out of Quiz
**Location**: `#quiz-overlay` HTML (~line 1134), `#quiz-nav` element  
**Status**: ✅ Implemented & Verified

**Problem**  
`#quiz-overlay` is `position:fixed; inset:0; z-index:52` — covers entire viewport including bottom bar (z-index:20). Avatar is `right:60px; z-index:60` — sits on top of anything at bottom-right. Student cannot navigate away from quiz.

**Final correct implementation**  
`#quiz-nav` must be:
- `position: fixed` (not absolute — needs to escape overlay stacking)
- `bottom: 16px; left: 20px` (bottom-LEFT — avatar never occupies left side)
- `z-index: 65` (above avatar at z-index:60)

```html
<div id="quiz-nav" style="
    position:fixed; bottom:16px; left:20px;
    display:flex; gap:10px; align-items:center; z-index:65;
">
    <button onclick="loadSection(curSec > 0 ? curSec - 1 : 0)">← PREV SECTION</button>
    <button onclick="loadSection(curSec < SECTIONS.length - 1 ? curSec + 1 : curSec)">SKIP QUIZ →</button>
</div>
```

**Verification**  
- [x] During quiz — PREV SECTION and SKIP QUIZ buttons visible bottom-left
- [x] Avatar does NOT overlap buttons
- [x] Clicking PREV navigates to previous section cleanly
- [x] Clicking SKIP QUIZ navigates to next section cleanly
- [x] Buttons are subtle at rest, brighter on hover

---

### VIDEO-BUFFER — Black Flash Between Beat Transitions
**Functions**: `showBeat` (~line 2019), `onTimeUpdate` (~line 2056)  
**Status**: ✅ Implemented & Verified

**Problem**  
`wan-vid-pre` preload buffer is filled by `preloadNext()` but `showBeat()` completely ignores it — every beat switch does a cold `wanVid.load()`. Preload also triggers at beat boundary (0 seconds lead time) instead of in advance.

**Fix A — `showBeat`: use buffer if ready**  
```js
var fullSrc = getMediaSrc(beat.src);
if (wanPre && wanPre.src && wanPre.src === fullSrc && wanPre.readyState >= 2) {
    wanVid.src = fullSrc;
    wanVid.currentTime = 0;
    wanVid.play().catch(function () { });
    console.log('[GAPLESS] Buffer swap beat ' + idx);
} else {
    wanVid.src = fullSrc; wanVid.load(); wanVid.play().catch(function () { });
}
```

**Fix B — `onTimeUpdate`: preload 3 seconds early**  
```js
if (activeIdx >= 0 && activeIdx + 1 < schedule.length) {
    var currentBeat = schedule[activeIdx];
    if (currentBeat.end && (currentBeat.end - t) <= 3.0) {
        preloadNext(activeIdx + 1);
    }
}
```

**Verification**  
- [x] Play through 3+ beat transitions in content section
- [x] No black frame visible between beats
- [x] Browser console shows `[GAPLESS] Buffer swap beat N` log entries
- [x] Falls back gracefully on slow network (no black screen — just cold load)

---

## PROMPT ISSUES

---

### PROMPT-001 — Global Director Renderer Enum Has Documentation Inconsistency
**File**: `director_global_prompt.txt` line 128  
**Status**: 🔴 Not implemented

**Problem**  
Line 128 lists valid renderer values as `"none", "text_to_video", "image_to_video", "manim"`. Note: Manim is NOT deprecated — LLM uses it when appropriate with a `renderer_reason`. However `"text_to_video"` is unused in V3 (recap uses `"image_to_video"`). The enum should match what is actually used.

**Fix**  
Update line 128 to:
```
Valid values: "none", "image_to_video", "manim"
```

**Verification**  
- [ ] New jobs do not output `renderer: "text_to_video"` for any section

---

### PROMPT-002 — Duplicate `section_type: "memory"` Line
**File**: `director_global_prompt.txt` lines 176–177  
**Status**: 🔴 Not implemented

**Problem**  
`section_type: "memory"` appears twice on consecutive lines — copy-paste leftover.

**Fix**  
Delete one of the duplicate lines.

---

### PROMPT-003 — Visual Prompt Enhancer Does Not Protect Source Image Beats
**File**: `visual_prompt_enhancer_prompt.txt`  
**Status**: 🔴 Not implemented

**Problem**  
When a beat has `image_source` (a real uploaded source image), the enhancer should use that image as the conditioning frame for `image_to_video` — generating an enhanced cinematic version of the actual source image. Currently the enhancer may generate new unrelated visual prompts, ignoring the source image entirely.

**Fix**  
Add rule to `visual_prompt_enhancer_prompt.txt`:
```
IF a beat has image_source (non-null, non-empty):
  → visual_type becomes "image_to_video"
  → image_prompt_start MUST describe the source image faithfully as the opening frame
  → image_prompt_end describes a subtle evolution (zoom, highlight, glow — same scene)
  → video_prompt describes slow concept-aligned motion over the image
  → Do NOT change the image_source value
  → Do NOT invent a different scene
  → The source image IS the start frame
```

---

## COMPLETE VERIFICATION CHECKLIST

Use this to sign off the full release:

### Pipeline
- [x] IMG-002: No absolute paths in `presentation.json`. No 404s in browser.
- [x] SUBST-001: Avatar speaks actual subject/grade in intro.
- [x] INDENT-001: `python3 -m py_compile core/pipeline_v3.py` clean.

### Player — Summary
- [x] SUMM-01: Bullets appear exactly when avatar speaks each one. Pause stops them.
- [x] SUMM-02: Intro sentence not shown as a bullet. Bullet count = number of objectives.

### Player — Quiz
- [x] QUIZ-HIDE: Card and options fully hidden during explanation. Video plays full screen with zero tint. Restores cleanly for next question.
- [x] SUB-DRIFT: Subtitle stays in sync after 5-second pause. No rush on resume.
- [x] SUB-QUIZ: No stale content subtitles during quiz. Question and explanation clips show correct subtitle text.
- [x] QUIZ-NAV: Buttons visible bottom-left, above avatar, not obstructed. Both navigate correctly.

### Player — Video
- [x] VIDEO-BUFFER: No black frames between beats. Console shows `[GAPLESS]` logs.

### Prompts
- [ ] PROMPT-001: Renderer enum updated in global director prompt.
- [ ] PROMPT-002: Duplicate memory line removed.
- [ ] PROMPT-003: Source image enhancer rule added.


