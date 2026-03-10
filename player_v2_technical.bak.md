# Player V2.js Technical Specification (V2.5 Compliant)

**Document Version**: 2.5.0  
**Last Updated**: 2026-01-10  
**Status**: Ready for Implementation  
**Purpose**: Technical reference for player_v2.js V2.5 Director Bible compliance

---

## V2.5 Bible Compliance Matrix

| Section Type | Bible Requirement | Implementation Status | `presentation.json` Fields |
|--------------|-------------------|----------------------|---------------------------|
| **INTRO** | Avatar ONLY (text_layer: HIDE, visual_layer: HIDE, avatar_layer: SHOW) | ✅ COMPLIANT | `section_type === 'intro'`, `avatar_video` |
| **SUMMARY** | Bullet points, time-synced reveal (visual_type: bullet_list, text_layer: SHOW) | ⚠️ NEEDS FIX | `visual_beats[].display_text`, `narration.segments[].start_time_sec` |
| **CONTENT** | Teach→Show toggle (Segment 1: text SHOW, visual HIDE; Segment 2: text HIDE, visual SHOW FULL) | ⚠️ NEEDS FIX | `video_path`, `flip_timing_sec`, `display_directives.action_type` |
| **EXAMPLE** | Same as Content (step-by-step with Manim/Video) | ⚠️ NEEDS FIX | Same as Content |
| **QUIZ** | 3-step dance (Introduce 15-20s → Pause 3-5s → Reveal 15-20s) | ❌ MISSING | `quiz_questions[]`, `display_directives.action_type === "pause"` |
| **MEMORY** | Flashcard flip (Front 10s → Pause 2s → Back 10s), Exactly 5 items | ❌ MISSING | `flashcards[].front`, `.back`, `display_directives.action_type === "flip_card"` |
| **RECAP** | Full-screen video ONLY (text: HIDE, visual: SHOW FULL, Exactly 5 segments) | ⚠️ NEEDS FIX | `section_type === 'recap'`, `beat_video_paths[]` |

### Bible Rule: Avatar Visibility
**Comparison Table (Line 82)**: Avatar = **Show** for ALL section types  
**Implementation**: Avatar layer MUST be visible (opacity: 1, z-index: 20) in ALL sections  
**Status**: ✅ Confirmed in plan

---

## Critical Requirements from V2.5 Bible

### 1. Content Section: "Teach → Then Show" (Line 37)
**Bible Quote**: "Segment 1 (Teach): Avatar explains concept. Visuals = Text/Diagrams. (texts: SHOW, visual: HIDE). Segment 2 (Show): Video/Manim demonstrates it. (text: HIDE, visual: SHOW (Full))."

**Implementation**:
```javascript
// TEACH Phase (based on display_directives or before flip_timing_sec)
contentLayer.style.opacity = '1';  // text/diagrams SHOW
avatarLayer.style.opacity = '1';   // avatar SHOW (overlay)
videoLayer.style.opacity = '0';    // visual HIDE

// SHOW Phase (triggered by flip_timing_sec or display_directives.action_type === "show_video")
contentLayer.style.opacity = '0';  // text HIDE
avatarLayer.style.opacity = '1';   // avatar SHOW (overlay) - ALWAYS VISIBLE
videoLayer.style.cssText = 'opacity: 1; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 15;';  // visual SHOW (FULL)
```

### 2. Quiz: 3-Step Dance (Lines 57-60)
**Bible Quote**: "Introduce: Read Question. (Visual: Question Text + Options). -> 15-20s. Pause: Silence. (Visual: Thinking Time). -> 3-5s (Strict). Reveal: Explain Answer. (Visual: Correct Option Highlight + \"Correct!\"). -> 15-20s."

**Implementation**: State machine with `display_directives.action_type`:
- `"introduce"`: Show question + options, play narration
- `"pause"`: Mute audio, show "Think..." for 3-5s (block UI)
- `"reveal_answer"`: Highlight correct option, play explanation

### 3. Memory: Flashcard Flip (Lines 67-70)
**Bible Quote**: "Front: The Term/Question. Back: The Mnemonic/Answer. Behavior: Front shows -> Pause -> Back Flips/Reveals. Timing: ~10s per side."

**Implementation**: CSS 3D transform with timing:
```css
.flashcard {
  transform-style: preserve-3d;
  transition: transform 1s;
}
.flashcard.flipped {
  transform: rotateY(180deg);
}
```

### 4. Recap: Full-Screen Video Only (Lines 75-78)
**Bible Quote**: "Visuals: FULL SCREEN VIDEO (Text Hidden)."

**Implementation**:
```javascript
if (section_type === 'recap') {
  contentLayer.style.display = 'none';  // Text HIDDEN
  videoLayer.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 15;';  // FULL SCREEN
  avatarLayer.style.opacity = '1';  // Avatar SHOW (overlay)
}
```

### 5. Pointer Resolution: 100% Fidelity (Lines 127-134)
**Bible Quote**: "The Director DOES NOT generate content text. It only generates **Pointers**. Director Output: `markdown_pointer: { \"start_phrase\": \"...\", \"end_phrase\": \"...\" }`. Rule: If a sentence is not in the source, it cannot be in the lesson."

**Implementation**: Prioritize `slide.markdown_content[]` over `slide.visual_content`:
```javascript
if (slide.markdown_content && slide.markdown_content.length > 0) {
  // Use verbatim source markdown
  renderMarkdownContent(slide.markdown_content);
} else {
  // Fallback to visual_content (legacy)
  console.warn('[V2.5] No markdown_content found - using fallback');
  renderVisualContent(slide.visual_content);
}
```

---

## V2.5 Time Source Architecture

**V2.5 Key Change:** NO separate MP3 audio files. The avatar video (MP4) contains embedded audio.

### Time Source Priority
```
1. Avatar Video (MP4) - PRIMARY (has embedded narration audio)
2. Timer Fallback - FALLBACK (when no avatar available)
```

### Code Implementation
```javascript
// From setupMediaSource() in player_v2.js
if (avatarPath && avatarVideo.src) {
  // PRIMARY: Use avatar video as time source
  activeTimeSource = avatarVideo;
  console.log('[V2.5] Using Avatar Video as Time Source');
} else {
  // FALLBACK: Use timer
  activeTimeSource = timerFallback;
  console.log('[V2.5] No avatar - using timer fallback');
}
```

### What This Enables
- ✅ Subtitle sync with avatar narration
- ✅ Progressive reveal synced to avatar timing
- ✅ Quiz/Memory timing based on avatar duration
- ✅ Simpler architecture (no MP3 generation needed)

---

## Implementation Plan Summary

### Issues to Fix (9 Total)

1. ❌ **Missing renderQuiz()** - Implement 3-step state machine
2. ⚠️ **Teach→Show not enforced** - Add layer toggling based on `flip_timing_sec` / `display_directives`
3. ⚠️ **Recap not full-screen** - Detect `section_type === 'recap'` and force video-only mode
4. ⚠️ **Summary bullets all at once** - Add time-synced reveal based on `segments[].start_time_sec`
5. ❌ **Missing renderMemory()** - Implement flashcard flip with CSS 3D transforms
6. ⚠️ **Subtitle positioning** - Move to bottom (`position: fixed; bottom: 20px; background: transparent`)
7. ✅ **Source markdown verification** - Verify `markdown_content` usage in `renderContent()`
8. ❌ **No media preloading** - Implement `preloadNextSection()` to buffer next slide's video/audio/avatar
9. ❌ **No fallback UI** - Add orange "Generating Video..." placeholder for missing media

### Sanity Checks Required

#### Unit Tests (`tests/test_player_v2_rendering.html`)
- Mock `presentation.json` with all 7 section types
- Test Quiz state machine (verify 3-5s pause duration)
- Test Content layer toggling (verify `videoLayer.style.position === 'fixed'`)
- Test Summary progressive reveal (verify bullets appear sequentially)
- Test Memory flip animation (verify CSS transform applied)
- Test subtitle positioning (verify `bottom: 20px`, `background: transparent`)

#### Sanity Check Script (`scripts/player_sanity_check.js`)
- Use Puppeteer to load player in headless browser
- Verify:
  1. Quiz pause phase enforces 3-5s delay
  2. Content video goes full-screen during "Show" phase
  3. Summary bullets reveal one-by-one
  4. Memory flashcards flip at correct timing
  5. Subtitle is at bottom with transparent background
  6. Next section media is preloaded (check Network tab)
  7. Fallback UI appears for missing media
  8. Avatar is ALWAYS visible (opacity: 1) in ALL sections
- Output: PASS/FAIL report with screenshots

#### Manual Verification
- Load real job (e.g., `jobs/a2010547`) in browser
- Navigate through each section type
- Use DevTools to inspect:
  - Content "Show" phase: `videoLayer` has `position: fixed, width: 100vw, height: 100vh`
  - Recap: `contentLayer` has `display: none`
  - Subtitle: Container has `position: fixed, bottom: 20px, background: transparent`
  - Memory: Flashcards have `transform: rotateY(180deg)` when flipped
  - Avatar: `avatarLayer.style.opacity === '1'` in ALL sections
- Take screenshots for walkthrough

---

## `presentation.json` Field Reference

### Section-Level Fields
- `section_type`: (`"intro"` | `"summary"` | `"content"` | `"example"` | `"quiz"` | `"memory"` | `"recap"`)
- `video_path`: Path to Manim/WAN video (e.g., `"videos/section_3_manim.mp4"`)
- `avatar_video`: Path to avatar video (e.g., `"videos/section_3_avatar.mp4"`)
- `audio_path`: ~~Deprecated in V2.5~~ - Audio comes from Avatar video (MP4)
- `flip_timing_sec`: Time in seconds to switch from Teach→Show (e.g., `12.5`)
- `beat_video_paths[]`: Array of video paths for multi-beat sections (used in Recap)

### Quiz-Specific Fields
- `quiz_questions[]`: Array of question objects
  - `.question`: Question text
  - `.options[]`: Array of option texts
  - `.correct_option`: Index of correct answer (0-based)

### Memory-Specific Fields
- `flashcards[]` or `memory_items[]`: Array of flashcard objects
  - `.front`: Front side text (term/question)
  - `.back`: Back side text (mnemonic/answer)

### Narration Fields
- `narration.segments[]`: Array of narration segment objects
  - `.text`: Narration text (also used for subtitles)
  - `.start_time_sec`: Start time in seconds
  - `.duration_seconds`: Duration of segment
  - `.display_directives`: Object controlling UI state
    - `.action_type`: (`"show_video"` | `"show_text"` | `"pause"` | `"reveal_answer"` | `"flip_card"` | `"introduce"`)
    - `.pause_duration_sec`: Duration of pause (for Quiz)
    - `.card_index`: Index of flashcard to flip (for Memory)

### Summary-Specific Fields
- `visual_beats[]`: Array of visual beat objects
  - `.display_text`: Bullet point text
  - `.visual_type`: Type of visual (`"bullet_list"`)

### Pointer Resolution Fields (Anti-Hallucination)
- `markdown_content[]`: Array of markdown lines (verbatim from source)
- `markdown_pointer`: Object with pointer data
  - `.start_phrase`: Starting phrase in source markdown
  - `.end_phrase`: Ending phrase in source markdown

---

## Code Won't Break - Backward Compatibility

### Fallback Strategy
All new features include fallbacks to ensure existing jobs don't break:

1. **Missing `display_directives`**: Fall back to `flip_timing_sec` for Content phase switching
2. **Missing `quiz_questions`**: Render as plain content with warning
3. **Missing `flashcards`**: Render as plain text with warning
4. **Missing `markdown_content`**: Use `visual_content` (legacy mode)
5. **Missing video files**: Show orange "Generating..." placeholder instead of error

### Non-Breaking Changes
- Subtitle repositioning: Pure CSS change, doesn't affect functionality
- Media preloading: Runs in background, doesn't block rendering
- Time-synced bullets: Renders all bullets initially (hidden), then reveals - old jobs see all bullets (same as before)

---

## Implementation Phases

### Phase 1: Core Renderers (No Breaking Changes)
- Add `renderQuiz()` function
- Add `renderMemory()` function
- Update `renderContent()` for Teach→Show toggle
- Update `renderSummary()` for progressive reveal

### Phase 2: UX Enhancements (Backward Compatible)
- Fix subtitle positioning (CSS only)
- Implement media preloading
- Add fallback UI for generating media

### Phase 3: Verification & Testing
- Create unit tests
- Create sanity check script
- Manual verification with real jobs
- Update walkthrough with screenshots

---

## Success Criteria

✅ All 7 section types render correctly per V2.5 Bible  
✅ Avatar is ALWAYS visible (confirmed in all sections)  
✅ Quiz enforces 3-5s pause (verified in tests)  
✅ Content video goes full-screen during "Show" phase (verified in DevTools)  
✅ Summary bullets appear sequentially (verified in tests)  
✅ Memory flashcards flip with animation (verified in DevTools)  
✅ Recap is full-screen video-only (verified in DevTools)  
✅ Subtitles are at bottom with transparent background (verified in DevTools)  
✅ Next section media is preloaded (verified in Network tab)  
✅ Fallback UI appears for generating media (verified with missing files)  
✅ Source markdown pointer resolution works (verified by prioritizing `markdown_content`)  
✅ All unit tests PASS  
✅ Sanity check script reports PASS  
✅ No existing jobs break (backward compatibility confirmed)

---

## References

- V2.5 Director Bible: `v2.5_Director_Bible.md`
- Player Implementation: `player/player_v2.js`
- Player CSS: `player/player_v2.css`
- Implementation Plan: `brain/6412e335-b649-41da-bf8b-eb7fae71ade2/implementation_plan.md`

**Ready for Implementation**: ✅ "Go ahead" approved
