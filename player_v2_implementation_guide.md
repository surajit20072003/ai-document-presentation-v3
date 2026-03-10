# Player V2.js V2.5 Compliance - Complete Implementation Guide

## Status: 🔴 CRITICAL FIXES REQUIRED

**Last Updated**: 2026-01-11

---

## Executive Summary

After comprehensive audit of `player_v2.js` (2700 lines), the following issues were found:

| Section Type | Status | Issue | Fix Required |
|--------------|--------|-------|--------------|
| **Summary** | 🔴 BROKEN | Bullets visible immediately | CSS specificity issue - need transition on reveal-hidden |
| **Memory** | 🔴 BROKEN | No flip animation | Missing `updateMemoryFlip()` function call |
| **Quiz** | ⚠️ PARTIAL | No quiz in test job | Function exists but untested |
| **Content** | 🔴 BROKEN | Text dumped | No progressive reveal for content |
| **Avatar** | 🔴 BROKEN | Shows idle | `avatar_video` missing from presentation.json |
| **Intro** | ✅ OK | Works | - |
| **Recap** | ✅ OK | Works | - |

---

## ROOT CAUSE ANALYSIS

### Issue 1: Summary Bullets Not Revealing Progressively

**Evidence**: All 4 bullets visible immediately in screenshot.

**Code Analysis**:
- `renderSummary()` (line 916-1026): Adds `reveal-hidden` class ✅
- `updateSummaryProgressiveReveal()` (line 363-401): Adds `reveal-visible` class ✅
- `handleTimeUpdateMain()` (line 347-359): Calls `updateSummaryProgressiveReveal()` ✅

**Root Cause**: The CSS `.summary-item` has `transition` which may cause initial state issues. Also, the `.reveal-hidden` needs to be applied BEFORE the element is rendered.

**Fix**: Add explicit transition and ensure opacity is 0 initially:

```css
/* player_v2.css - Line 1002 - REPLACE */
.summary-item {
  opacity: 0;
  transform: translateY(15px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.summary-item.reveal-visible {
  opacity: 1;
  transform: translateY(0);
}
```

---

### Issue 2: Memory Flashcards Not Flipping

**Evidence**: All 5 flashcards visible as text cards, no flip.

**Code Analysis**:
- `renderMemory()` (line 1264-1294): Creates cards with `.flashcard` class ✅
- **NO `updateMemoryFlip()` function exists!** ❌
- **NO flip trigger in `handleTimeUpdateMain()`!** ❌

**Root Cause**: The flip animation was never implemented. Only render logic exists.

**Fix**: Add `updateMemoryFlip()` and call it from `handleTimeUpdateMain()`:

```javascript
// ADD after updateQuizProgressiveReveal() - around line 450

// V2.5: Memory Flashcard Flip - Progressive reveal based on timing
function updateMemoryFlip() {
  const slide = slides[currentSlideIndex];
  if (!slide || slide.section_type !== 'memory') return;

  const flashcards = slide.flashcards || slide.memory_items || [];
  if (flashcards.length === 0) return;

  const currentTime = getTime();
  const totalDuration = getDuration() || 60;
  
  // Each flashcard gets equal time: show front, then flip to back
  const timePerCard = totalDuration / flashcards.length;
  const flipDelay = timePerCard * 0.5; // Flip at 50% of each card's time

  for (let i = 0; i < flashcards.length; i++) {
    const card = document.getElementById(`flashcard-${i}`);
    if (!card) continue;

    const cardStartTime = i * timePerCard;
    const cardFlipTime = cardStartTime + flipDelay;

    // Show card (remove hidden) when its time starts
    if (currentTime >= cardStartTime && !card.classList.contains('memory-visible')) {
      card.classList.add('memory-visible');
      console.log(`[V2.5] Memory: Showing card ${i + 1}`);
    }

    // Flip card after delay
    if (currentTime >= cardFlipTime && !card.classList.contains('flipped')) {
      card.classList.add('flipped');
      console.log(`[V2.5] Memory: Flipped card ${i + 1}`);
    }
  }
}
```

**Also update handleTimeUpdateMain()** (line 347-359):

```javascript
function handleTimeUpdateMain() {
  updateTimeline();
  updateContentPages();
  syncBeatVideoToAudio(getTime());
  updateDisplayState();
  updateSummaryProgressiveReveal();
  updateMemoryFlip();  // <-- ADD THIS LINE
}
```

---

### Issue 3: Avatar Not Loading

**Evidence**: Avatar files exist (`section_1_avatar.mp4`, `section_2_avatar.mp4`) but player shows idle.

**Root Cause**: `avatar_video` field missing from `presentation.json`.

The `AvatarGenerator._update_artifacts()` function is failing silently.

**Quick Fix** (run after job completes):
```powershell
python scripts\patch_avatar_paths.py player\jobs\{job_id}
```

**Permanent Fix**: Debug `core/agents/avatar_generator.py` line 170-243.

---

### Issue 4: Content Section Text Dumped

**Evidence**: All paragraphs visible at once, no progressive reveal.

**Root Cause**: `renderContent()` does not add `reveal-hidden` class to content items.

**Fix**: Modify `renderContent()` to add progressive reveal classes:

```javascript
// In renderContent() around line 1028+ when creating paragraph/bullet elements:
// ADD reveal-hidden class similar to summary:
item.className = 'content-paragraph reveal-hidden';
item.id = `content-item-${i}`;
```

And add corresponding `updateContentProgressiveReveal()` function.

---

## CSS FIXES REQUIRED

### File: `player_v2.css`

#### Fix 1: Summary Reveal (Line 1001-1011)
```css
/* REPLACE existing rules */
.summary-item {
  opacity: 0;
  transform: translateY(15px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.summary-item.reveal-visible {
  opacity: 1;
  transform: translateY(0);
}
```

#### Fix 2: Memory Flashcard Flip (Add after line 445)
```css
/* Flashcard 3D Flip */
.flashcard-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
  padding: 20px;
  perspective: 1000px;
}

.flashcard {
  width: 200px;
  height: 180px;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.8s ease;
  cursor: pointer;
  opacity: 0;
  transform: translateY(20px);
}

.flashcard.memory-visible {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.flashcard.flipped {
  transform: rotateY(180deg);
}

.flashcard-front,
.flashcard-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px;
  border-radius: 12px;
  box-sizing: border-box;
  text-align: center;
}

.flashcard-front {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.flashcard-back {
  background: linear-gradient(135deg, #f093fb, #f5576c);
  color: white;
  transform: rotateY(180deg);
}
```

---

## JAVASCRIPT FIXES REQUIRED

### File: `player_v2.js`

#### Fix 1: Add updateMemoryFlip() (After line 450)
```javascript
// V2.5: Memory Flashcard Flip - Progressive reveal based on timing
function updateMemoryFlip() {
  const slide = slides[currentSlideIndex];
  if (!slide || slide.section_type !== 'memory') return;

  const flashcards = slide.flashcards || slide.memory_items || [];
  if (flashcards.length === 0) return;

  const currentTime = getTime();
  const totalDuration = getDuration() || 60;
  
  // Each flashcard gets equal time: show front, then flip to back
  const timePerCard = totalDuration / flashcards.length;
  const flipDelay = timePerCard * 0.5; // Flip at 50% of each card's time

  for (let i = 0; i < flashcards.length; i++) {
    const card = document.getElementById(`flashcard-${i}`);
    if (!card) continue;

    const cardStartTime = i * timePerCard;
    const cardFlipTime = cardStartTime + flipDelay;

    // Show card (remove hidden) when its time starts
    if (currentTime >= cardStartTime && !card.classList.contains('memory-visible')) {
      card.classList.add('memory-visible');
      console.log(`[V2.5] Memory: Showing card ${i + 1}`);
    }

    // Flip card after delay
    if (currentTime >= cardFlipTime && !card.classList.contains('flipped')) {
      card.classList.add('flipped');
      console.log(`[V2.5] Memory: Flipped card ${i + 1}`);
    }
  }
}
```

#### Fix 2: Update handleTimeUpdateMain() (Line 347-359)
```javascript
function handleTimeUpdateMain() {
  updateTimeline();
  updateContentPages();
  syncBeatVideoToAudio(getTime());
  updateDisplayState();
  updateSummaryProgressiveReveal();
  updateMemoryFlip();  // ADD THIS LINE
}
```

#### Fix 3: Update renderMemory() to hide cards initially (Line 1276)
```javascript
// CHANGE line 1276 from:
cardDiv.className = 'flashcard';

// TO:
cardDiv.className = 'flashcard'; // Card starts invisible, updateMemoryFlip() reveals
```

---

## IMAGE INJECTION FIX (Pipeline)

### Problem
LLM doesn't generate `visual_type: image` even when source has images.

### Solution
Modify `inject_missing_image_ids()` in `partition_director_generator.py` to:

1. Scan source markdown for `![alt](filename)` patterns
2. For each image found, check if ANY visual_beat references it
3. If not, **CREATE** a new visual_beat with `visual_type: image`

```python
# In inject_missing_image_ids() - ADD after line 125:

# Strategy 6: FORCE CREATE image beats if source has images but none were generated
if injected_count == 0 and source_image_map:
    # No injections happened - LLM probably didn't generate any diagram/image visual_types
    # Force create them based on source images
    for section in sections:
        visual_beats = section.get("visual_beats", [])
        for img_filename, alt_text in source_image_map.items():
            # Check if this image is already referenced
            already_referenced = any(
                beat.get("image_id") == img_filename 
                for beat in visual_beats
            )
            if not already_referenced:
                new_beat = {
                    "beat_id": f"beat_img_{len(visual_beats) + 1}",
                    "visual_type": "image",
                    "image_id": img_filename,
                    "display_text": alt_text or "Diagram",
                    "start_time": 0
                }
                visual_beats.append(new_beat)
                injected_count += 1
                logger.info(f"[ImageInjection] FORCE CREATED image beat for '{img_filename}'")
        section["visual_beats"] = visual_beats
```

---

## TESTING CHECKLIST

After implementing fixes:

- [ ] Summary bullets reveal one-by-one during playback
- [ ] Memory flashcards appear one-by-one and flip to show back
- [ ] Quiz answers reveal after "pause" segment
- [ ] Content text reveals progressively
- [ ] Avatar video plays when file exists
- [ ] Images display when source has them
- [ ] Timer fallback works (no audio needed)
- [ ] No console errors

---

## QUICK TEST COMMANDS

```powershell
# Patch avatar paths for current job
python scripts\patch_avatar_paths.py player\jobs\0f1eaff8

# Restart API server to load changes
# Stop current: Ctrl+C
python .\api\app.py
```

---

## Files Modified

| File | Changes |
|------|---------|
| `player/player_v2.css` | Summary reveal CSS, Flashcard 3D flip CSS |
| `player/player_v2.js` | Add `updateMemoryFlip()`, update `handleTimeUpdateMain()` |
| `core/partition_director_generator.py` | Force-create image visual beats |
