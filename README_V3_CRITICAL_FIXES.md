# V3 Critical Bug Fixes

## 1. IMG-002 — Image Path Normalization

**Problem:** `image_source` fields in `presentation.json` sometimes contained absolute OS paths (e.g. `/nvme0n1-disk/.../images/foo.png`) which the browser cannot resolve, causing 404 errors and broken images.

**Solution (already implemented):**
- `core/pipeline_v3.py` Phase 1.5 runs unconditionally after Phase 1 (Director). It scans both `images/` and `generated_images/` subdirectories in the job folder and replaces any absolute or mismatched `image_source` value with the correct relative path (e.g. `images/foo.png`).
- `render/image/image_generator.py` `generate_image_for_beat()` returns `os.path.join("images", os.path.basename(abs_path))` — always a relative path.

---

## 2. SUBST-001 — Placeholder Substitution Before TTS

**Problem:** `{{subject}}` and `{{grade}}` placeholders in narration scripts were only substituted inside the `if not skip_avatar:` block in `pipeline_v3.py`. In `dry_run=True` or `skip_avatar=True` mode, the substitution never ran, leaving `{{subject}}` as literal text in `presentation.json` and in spoken TTS audio.

**Solution:**
- Added **Phase 1.6** in `core/pipeline_v3.py`, inserted unconditionally before Phase 3.3 (Avatar Generation).
- The call to `substitute_placeholders(presentation, subject, grade)` now always runs regardless of dry_run / skip_avatar flags.
- Removed the duplicate late call from inside the avatar block.

```python
# Phase 1.6: Placeholder Substitution (pipeline_v3.py ~L334)
log("placeholder_sub", "Phase 1.6: Substituting {{subject}} / {{grade}} placeholders...")
presentation = substitute_placeholders(presentation, subject=subject, grade=str(grade))
log("placeholder_sub", "✅ Phase 1.6 complete.")
```

---

## 3. SUMM-01 — Summary Bullets Sync to Avatar Time

**Problem:** Summary section bullets appeared all at once instead of in sync with when the avatar spoke each segment.

**Solution (already implemented):**
- `player/player_v3.html` `initSummarySection()` uses a `timeupdate` event listener on the avatar video.
- Uses `seg.start_seconds` if available, otherwise falls back to `i * 5` seconds.
- Each bullet's `show` class is added only when `avEl.currentTime >= threshold`.

---

## 4. SUMM-02 — Remove Intro Sentence from Summary Bullets

**Problem:** The first narration segment in Summary sections has `purpose: "introduce"` — an avatar intro line like "In this section we will cover…" It was being rendered as a bullet point alongside the actual learning objectives.

**Solution (already implemented):**
- `player/player_v3.html` `buildSummaryHTML()` filters out segments with `purpose: "introduce"`:
```js
var bulletSegments = allSegments.filter(function (seg) {
    return seg.purpose !== 'introduce';
});
```

---

## 5. QUIZ-EXP — Explanation Video Visible Behind Quiz Overlay

**Problem:** When a quiz question was answered, the `showExplanationVisual()` function played a Manim/WAN video behind the quiz overlay. But the overlay (`#quiz-overlay`) was fully opaque (`rgba(13,17,23,0.96)`), making the explanation video completely invisible.

**Solution:**
- In `player/player_v3.html` `onAnswer()`, after `showExplanationVisual(q)` is called and before the explanation audio clip plays, the overlay and card are dimmed:

```js
// QUIZ-EXP: Dim overlay so explanation video is visible behind it
var ovEl   = document.getElementById('quiz-overlay');
var cardEl = document.getElementById('quiz-question-card');
var optsEl = document.getElementById('quiz-options');
if (ovEl)   ovEl.style.background   = 'rgba(13,17,23,0.4)';
if (cardEl) cardEl.style.background = 'rgba(22,27,34,0.45)';
if (optsEl) optsEl.style.opacity    = '0.55';
```
- After the explanation clip finishes, the original backgrounds and opacity are fully restored before advancing to the next question.
