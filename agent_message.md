# Bug Fix Implementation Plan
**Project**: AI Document Presentation V3  
**Date**: 2026-03-25  
**Priority**: All issues are 🔴 Critical — fix in order listed

---

## Issue Index

| ID | Issue | File | Status |
|---|---|---|---|
| IMG-002 | Image 404 — missing `images/` path prefix | `pipeline_v3.py`, `image_generator.py` | 🔴 Open |
| SUBST-001 | `{{subject}}` / `{{grade}}` never substituted before avatar generation | Pipeline stitcher | 🔴 Open |
| SUMM-01 | Summary bullets reveal at wall-clock intervals, not avatar clock | `player_v3.html` | 🔴 Open |
| SUMM-02 | Intro sentence renders as bullet #0 in summary | `player_v3.html` | 🔴 Open |
| QUIZ-EXP | Explanation video invisible behind opaque quiz overlay | `player_v3.html` | 🔴 Open |

---

## IMG-002 — Image Path Normalization

### Problem
`image_generator.py` returns full absolute disk paths like:
```
/nvme0n1-disk/nvme01/ai-document-presentation-v3/jobs/abc123/images/photo.png
```
These get written into `presentation.json` as `image_source` values. The browser cannot resolve absolute server paths — result is a 404 and a blank screen where the image should appear.

### Root Cause — Two places need fixing

**1. `pipeline_v3.py` — Phase 1.5 gate**

The path normalization in Phase 1.5 is gated behind `if saved_images:`, so it only runs when PDF source images were extracted. Jobs without PDF images skip it entirely, leaving absolute paths in the JSON.

**2. `image_generator.py` — Return value**

`generate_image_for_beat()` returns the full absolute path of the saved image instead of a path relative to `output_dir`.

---

### Fix 1 — `pipeline_v3.py`

**Remove the `if saved_images:` gate from Phase 1.5.**

```python
# BEFORE — Phase 1.5 only runs when saved_images is populated
if saved_images:
    _fix_image_sources(presentation_data, output_dir)

# AFTER — always run path normalization
_fix_image_sources(presentation_data, output_dir)
```

**Update `_fix_image_source()` to strip absolute prefixes and scan both image directories:**

```python
def _fix_image_source(image_source: str, output_dir: str) -> str:
    """
    Normalize an image_source path to be relative to output_dir.
    Strips any absolute path prefix, then searches images/ and
    generated_images/ for a filename stem match.
    Returns the relative path if found, or the cleaned filename if not.
    """
    if not image_source:
        return image_source

    # Step 1 — strip absolute prefix down to bare filename
    filename = os.path.basename(image_source)
    stem = os.path.splitext(filename)[0]

    # Step 2 — search images/ then generated_images/ for a stem match
    for subdir in ['images', 'generated_images']:
        search_dir = os.path.join(output_dir, subdir)
        if not os.path.isdir(search_dir):
            continue
        for f in os.listdir(search_dir):
            if os.path.splitext(f)[0] == stem:
                return os.path.join(subdir, f)  # e.g. "images/photo.png"

    # Fallback — return bare filename (better than an absolute path)
    return filename
```

---

### Fix 2 — `image_generator.py`

**Update `generate_image_for_beat()` to return a relative path.**

```python
# BEFORE — returns absolute path
saved_path = os.path.join(output_dir, 'generated_images', filename)
image.save(saved_path)
return saved_path  # e.g. /nvme0n1.../generated_images/abc.png

# AFTER — return relative path only
saved_path = os.path.join(output_dir, 'generated_images', filename)
image.save(saved_path)
return os.path.join('generated_images', filename)  # e.g. generated_images/abc.png
```

---

### Verification
1. Run a job that does NOT include a PDF with images.
2. Open `presentation.json` and search for `image_source`.
3. All values must be in the form `images/filename.png` or `generated_images/filename.png`.
4. No value should contain `/nvme`, `/home`, or any absolute path segment.
5. Load the player — confirm no 404 errors in the browser console for image files.

---

## SUBST-001 — `{{subject}}` / `{{grade}}` Placeholder Substitution

### Problem
The Global Director prompt instructs the LLM to write the intro narration as:
```
"Namaste! Welcome to our lesson on {{subject}} for Grade {{grade}}."
```
Using literal placeholder variables that the pipeline is supposed to substitute. However, the avatar is being generated **before** substitution happens, so the TTS speaks the string `{{subject}}` and `{{grade}}` verbatim to the student.

### Fix — Pipeline stitcher / pre-avatar step

Add a substitution pass **before** the avatar generation task is queued. This must run on the full narration text of every section.

```python
def substitute_placeholders(presentation_data: dict, subject: str, grade: str) -> dict:
    """
    Replace {{subject}} and {{grade}} in all narration text fields
    before avatar generation is triggered.
    Must be called after Director output is stitched but before
    avatar tasks are queued.
    """
    replacements = {
        '{{subject}}': subject,
        '{{grade}}': str(grade),
    }

    def replace_in_value(val):
        if isinstance(val, str):
            for placeholder, replacement in replacements.items():
                val = val.replace(placeholder, replacement)
            return val
        elif isinstance(val, dict):
            return {k: replace_in_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [replace_in_value(item) for item in val]
        return val

    return replace_in_value(presentation_data)
```

**Call site — immediately after director output is parsed, before avatar generation:**

```python
# In pipeline_v3.py or wherever avatar tasks are dispatched
presentation_data = substitute_placeholders(
    presentation_data,
    subject=job_config['subject'],
    grade=job_config['grade']
)
# NOW queue avatar generation
queue_avatar_tasks(presentation_data)
```

### Verification
1. Run a job with `subject = "Biology"` and `grade = "10"`.
2. Check the intro `narration.full_text` in `presentation.json` — must read:
   `"Namaste! Welcome to our lesson on Biology for Grade 10."`
3. The avatar MP4 audio must speak the actual subject and grade, not placeholder text.

---

## SUMM-01 — Summary Bullets Not Synced to Avatar

### Problem
`initSummarySection()` in `player_v3.html` reveals bullet points at fixed wall-clock intervals:
```js
timers.push(setTimeout(..., 400 + i * 1800));  // every 1.8 seconds regardless of speech
```
This is completely disconnected from the avatar. Bullets appear too early or too late depending on how fast the avatar is speaking. The narration segments already have `start_seconds` authored by the Director — the player just ignores them.

### Fix — `player_v3.html`, function `initSummarySection`

**Replace the entire function:**

```js
function initSummarySection(sec) {
    if (!sec.narration || !sec.narration.segments) return;
    var segments = sec.narration.segments;
    var sectionAtLoad = curSec;
    var avEl = document.getElementById('av-vid');

    // Hide all bullets on entry
    segments.forEach(function (_, i) {
        var el = document.getElementById('sb-' + sec.section_id + '-' + i);
        if (el) el.classList.remove('show');
    });

    function onTimeUpdate() {
        if (curSec !== sectionAtLoad) {
            avEl.removeEventListener('timeupdate', onTimeUpdate);
            return;
        }
        var t = avEl.currentTime;
        segments.forEach(function (seg, i) {
            // Use start_seconds if available, fall back to accumulated duration
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

---

## SUMM-02 — Intro Sentence Renders as Bullet #0

### Problem
The Global Director generates the first summary segment as:
```json
{ "segment_id": "seg_1", "text": "Here are the key learning objectives for today's lesson.", "purpose": "introduce" }
```
`buildSummaryHTML()` maps every segment to a numbered bullet — including this intro sentence. The student sees it as bullet #1 alongside the actual learning objectives, which is incorrect.

### Fix — `player_v3.html`, function `buildSummaryHTML`

**Filter out `purpose: "introduce"` segments before building bullet items:**

```js
function buildSummaryHTML(sec) {
    var allSegments = (sec.narration && sec.narration.segments) ? sec.narration.segments : [];

    // Only render actual objectives — skip the intro sentence
    var bulletSegments = allSegments.filter(function (seg) {
        return seg.purpose !== 'introduce';
    });

    var items = bulletSegments.slice(0, 6).map(function (seg, i) {
        // IMPORTANT: use the original segment index for the DOM id
        // so initSummarySection can still find it by segment position
        var origIdx = allSegments.indexOf(seg);
        return '<div class="sbullet" id="sb-' + sec.section_id + '-' + origIdx + '">' +
            '<div class="sbullet-n">' + (i + 1) + '</div>' +
            '<div class="sbullet-t">' + esc((seg.text || '').substring(0, 120)) + '</div></div>';
    }).join('');

    return '<div style="align-items:flex-start;max-width:680px;margin:0 auto;width:100%;display:flex;flex-direction:column;gap:10px">' +
        '<div class="sum-hd">By the end of this section, you will...</div>' + items + '</div>';
}
```

> **Note**: The DOM id is keyed to the **original segment index** (not the bullet index) so that `initSummarySection`'s `timeupdate` listener can find the right element by segment position. Both fixes (SUMM-01 and SUMM-02) must be applied together.

---

## QUIZ-EXP — Explanation Video Hidden Behind Quiz Overlay

### Problem
After a student answers a quiz question, `showExplanationVisual()` correctly starts playing the explanation video into `manim-layer` (z-index: 4) or `wan-layer` (z-index: 1). However, `#quiz-overlay` sits at **z-index: 52** with a near-opaque background:

```css
background: rgba(13,17,23,0.96);  /* essentially solid black */
```

The explanation video is playing but completely invisible. The student sees only the dark overlay.

### Why the overlay alone is not enough

The `#quiz-overlay` div has `background: rgba(13,17,23,0.96)`. Making it semi-transparent is step one, but it is not enough by itself. The **child elements inside the overlay also have solid backgrounds**:

```html
<!-- quiz-question-card -->
background: #161b22          ← solid, blocks the video

<!-- option buttons (created dynamically) -->
background: #21262d          ← solid, blocks the video
```

Even with the overlay at 55% opacity, the card and buttons remain fully opaque blocks sitting on top of the video. The video would only appear in the small padding gaps around the card — barely visible. All three layers need to be dimmed together.

---

### Fix — `player_v3.html`, function `showExplanationVisual` and `onAnswer`

**Step 1 — In `showExplanationVisual`, dim the overlay AND the inner card:**

```js
function showExplanationVisual(q) {
    var ev = q.explanation_visual;
    if (!ev) return;

    var vpath = ev.video_path;
    if (!vpath && ev.image_to_video_beats && ev.image_to_video_beats.length > 0) {
        vpath = ev.image_to_video_beats[0].video_path || null;
    }
    if (!vpath) return;

    // Dim overlay + card + options so video layer shows through all of them
    document.getElementById('quiz-overlay').style.background = 'rgba(13,17,23,0.4)';
    var card = document.getElementById('quiz-question-card');
    var opts = document.getElementById('quiz-options');
    if (card) card.style.background = 'rgba(22,27,34,0.45)';
    if (opts) opts.style.opacity = '0.55';

    var renderer = ev.renderer || 'manim';
    var manimLayer = document.getElementById('manim-layer');
    var manimVid = document.getElementById('manim-vid');
    var wanLayer = document.getElementById('wan-layer');
    var wanVid = document.getElementById('wan-vid');

    manimLayer.classList.remove('on');
    wanLayer.classList.remove('on');

    if (renderer === 'manim') {
        manimVid.src = getMediaSrc(vpath);
        manimVid.load();
        manimVid.play().catch(function () { });
        manimLayer.classList.add('on');
    } else {
        wanVid.src = getMediaSrc(vpath);
        wanVid.load();
        wanVid.play().catch(function () { });
        wanLayer.classList.add('on');
    }
}
```

**Step 2 — Restore all three backgrounds before advancing to the next question.**

Find the `setTimeout` inside `onAnswer` that calls `showQuestion(qIdx)` and prepend the restore:

```js
// BEFORE
timers.push(setTimeout(function () {
    document.getElementById('manim-layer').classList.remove('on');
    document.getElementById('wan-layer').classList.remove('on');
    qIdx++;
    showQuestion(qIdx);
}, 900));

// AFTER
timers.push(setTimeout(function () {
    // Restore full opacity on all three elements before next question
    document.getElementById('quiz-overlay').style.background = 'rgba(13,17,23,0.96)';
    var card = document.getElementById('quiz-question-card');
    var opts = document.getElementById('quiz-options');
    if (card) card.style.background = '#161b22';
    if (opts) opts.style.opacity = '1';

    document.getElementById('manim-layer').classList.remove('on');
    document.getElementById('wan-layer').classList.remove('on');
    qIdx++;
    showQuestion(qIdx);
}, 900));
```

### Verification
1. Open a presentation with a quiz that has `explanation_visual.video_path` populated.
2. Answer a question — the explanation video must be **clearly visible** playing behind the dimmed question card and option buttons.
3. After the explanation clip ends, all three elements must return to full opacity/solid before the next question appears.
4. If no `explanation_visual` or no `video_path`, behaviour must be unchanged (only fallback text shown).

---

## Testing Checklist

After all fixes are applied, run through this checklist end-to-end:

- [ ] **IMG-002**: Job with no PDF images — `presentation.json` has only relative `images/` paths, no absolute paths. No 404s in browser console.
- [ ] **SUBST-001**: Intro avatar speaks the actual subject and grade, not `{{subject}}` and `{{grade}}`. /nvme0n1-disk/nvme01/ai-document-presentation-v3/core/prompts/director_global_prompt.txt
- [ ] **SUMM-01**: Summary bullet points appear at the exact moment the avatar speaks each objective. Pause the avatar mid-summary — bullets must stop appearing.
- [ ] **SUMM-02**: The intro sentence ("Here are the key learning objectives…") does NOT appear as a numbered bullet.
- [ ] **QUIZ-EXP**: After answering a quiz question, the explanation video plays and is clearly visible behind the quiz card. Overlay returns to full opacity on next question.