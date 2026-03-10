# Player V2.js Technical Specification (V2.5.5 Production)

**Document Version**: 2.5.5
**Last Updated**: 2026-01-18
**Status**: Live / Production
**Purpose**: Technical reference for player_v2.js V2.5 Director Bible compliance

---

## 1. V2.5.5 Core Architecture

### Time Source Handling
1. **Primary**: Avatar Video (`activeTimeSource = avatarVideo`)
   - The avatar MP4 contains the authoritative audio track.
2. **Fallback**: Timer (`activeTimeSource = timerFallback`)
   - Used if no avatar is present.
   - Simulates playback for testing/development.

### Multi-Language Switching (New in V2.5.8)
The player supports real-time switching between avatar languages:
1. **Detection**: Checks `presentation.avatar_languages` for available regional tracks.
2. **Logic**: Swaps `avatarVideo` src to the corresponding `avatars/{lang}/section_{id}_avatar.mp4`.
3. **Sync**: Maintains playback timestamp during switching for a seamless experience.

### Beat Synchronization Engine (New in V2.5.5)
The player now uses a dual-strategy beat engine handled by `updateContentProgressiveReveal()`:

1. **Segment-Based Sync (Precision)**:
   - Uses `segment_id` mapping to link visual beats to exact video timestamps.
   - `beat.segment_id` -> `segmentTimeMap[segment_id].startTime`
   - **Critical for Manim**: Ensures text overlays appear exactly when the corresponding video segment starts/ends.

2. **Timestamp-Based Sync**:
   - Uses raw seconds (`beat.start_time`) if provided.

3. **Fallback (Distribution)**:
   - If no timing data exists, distributes beats evenly across the "Teach" phase duration (70% of total).

---

## 2. Key Functions Reference

### `applyV25DisplayDirectives(slide)`
The "Brain" of the V2.5 layout engine. Runs on every timeupdate.
- **Input**: `slide.narration.segments`
- **Logic**: Determines current segment based on time.
- **Action**: Reads `display_directives` (text_layer, visual_layer) to toggle:
  - `contentLayer` (Opacity 0/1)
  - `videoLayer` (Position Fixed/Hidden)

### `updateContentProgressiveReveal()`
Handles the appearance of bullet points, diagrams, and formulas.
- **Logic**: Checks `beat.segment_id` against current playback time.
- **Action**: Toggles `.reveal-visible` class on beat elements.
- **Math**: Triggers `typesetMath()` when new content appears.

### `buildBeatPlaylistWithTiming(slide)`
Manages "Beat Videos" for WAN/Recap sections (where one section = multiple video clips).
- **Input**: `segment.beat_videos` (Array of video paths)
- **Output**: `beatVideoPlaylist` (Array of {startTime, endTime, videoPath})
- **Behavior**: Seamlessly swaps the `contentVideo` src as playback progresses across segments.

### `renderQuiz(slide)`
Implements the strict "3-Step Dance" state machine:
1. **Introduce**: Show Question + Options.
2. **Pause**: Hard freeze for 3-5s (UI indicates "Think...").
3. **Reveal**: Highlight correct answer & show explanation.

### `renderMemory(slide)`
Handles CSS 3D Flashcards.
- **Animation**: Adds `.flipped` class based on calculated `flip_timing`.
- **CSS**: Uses `transform: rotateY(180deg)` and `backface-visibility: hidden`.

---

## 3. Data Structure Reference (`presentation.json`)

### Section Types
- `intro`: Avatar Only. Verify `text_layer: hide`.
- `summary`: Bullet List. Verified `visual_beats`.
- `content`: Teach/Show. Verified `display_directives`.
- `quiz`: 3-Step. Verified `quiz_questions`.
- `memory`: Flashcards. Verified `flashcards`.
- `recap`: Cinematic Video. Verified `renderer: video`.

### Critical Fields
- `segment_id`: **REQUIRED** for V2.5 beat sync.
- `beat_videos`: Array of video file IDs (e.g., `["topic_5_seg_1.mp4"]`).
- `markdown_pointer`: Used for Anti-Hallucination text resolution.
- `avatar_languages`: Map of available regional avatar tracks for real-time switching.

---

## 4. Markdown & Text Rendering
- **Engine**: `marked.js`
- **Sanitization**: `DOMPurify` (if available)
- **Features**:
  - Tables: Rendered with `.md-table` class.
  - LaTeX: Preserved via `<<<LATEX>>>` placeholders during markdown parsing, then restored for MathJax.

---

## 5. Backward Compatibility
The player maintains fallback logic for pre-V2.5 jobs:
- If `segment_id` is missing -> Uses even distribution.
- If `marked.js` is missing -> Falls back to simple regex parser.
- If `beat_videos` is missing -> Uses legacy `video_path` (single video).

