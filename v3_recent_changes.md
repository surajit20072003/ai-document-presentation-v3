# Recent Changes to V3 Player (`player_v3.html`)

Per your request, I have stopped making code changes. Here is a summary of the exact modifications that were recently applied to `player_v3.html` across the last few iterations, and my assessment of why they might be failing in the browser:

## 1. Avatar WebGL Chroma Key (Green Screen Removal)
**What was changed:**
- Replaced the CPU-heavy DOM green-screen logic with a GPU-accelerated WebGL shader.
- Added a `<canvas id="av-canvas" style="aspect-ratio:9/16;width:100%;display:block;">` inside the `#av-overlay` container.
- Scaled the original `<video id="av-vid">` to 1x1 pixels and made it transparent so it continues to play audio and act as the master clock, while the `canvas` renders the visuals.
- Implemented `initAvatarWebGL()` which uses Three.js (`THREE.ShaderMaterial`) to read the video texture, scan for the green color (`0x00ff00`), and calculate transparency using a `similarity` and `smoothness` threshold.

**Why it's failing / distorting size:**
- **Green Screen persists:** The specific shade of green in the avatar video might not perfectly match the hardcoded `0x00ff00` key color, or the `similarity` threshold (currently `0.28`) is too strict/loose for the lighting in the video. If the shader compiles successfully, it will still render the video frame but fail to make the background transparent if the green color distance is out of bounds.
- **Screwed up avatar size:** The WebGL `renderer.setSize()` relies on `canvas.clientWidth` and `canvas.clientHeight`. Because the `<video>` element was shrunk to 1x1, the parent `#av-overlay` container (which might not have a hardcoded `height` in CSS, only `width`) collapses, causing the `aspect-ratio: 9/16` on the canvas to behave unpredictably. This squeezes or distorts the canvas.

## 2. Hiding Subtitles During Recap
**What was changed:**
- Located the two places in the Javascript where subtitles are dynamically fetched from the JSON narration beats (`loadVideoScene` and `loadThreejsScene`).
- Inside the heartbeat loop `playNextBeat()`, added a condition: `var isRecap = (sec.section_type === 'recap' || sec.type === 'recap');`.
- Updated the display logic so that if `isRecap` is true, it explicitly sets `subtitleEl.style.display = 'none';` instead of injecting text.

**Why it's failing:**
- Even though the check fires during `init`, there is likely another interval or function in the codebase (perhaps tied to the `Three.js` loop or a master presentation clock) that forcefully loops over the `narration.segments` and re-injects the text into `subtitleTextEl.innerText = beatText`, immediately overriding the `display: none` we set when the beat changes. The screenshot clearly shows the exact first beat's text from `presentation.json` being rendered inside `#subtitle-overlay`.

## 3. General CSS Adjustments
**What was changed:**
- Increased general font sizes across `.tb-title`, `.intro-sub`, and `.quiz-q` to make text more readable.

---

### Recommended Gap Fill (When we resume)
If you wish to fix these later, the plan would be:
1. **Avatar Size:** Restore the `#av-overlay` explicit sizing in CSS, or let the invisible `<video>` keep its full size but give it `opacity: 0.01` and absolute position so it stretches the container perfectly for the canvas.
2. **Avatar Green:** Add a color-picker or auto-sampling function to find the exact background green of the first frame instead of hardcoding `0x00ff00`, or adjust the shader's `similarity` threshold.
3. **Subtitles:** Search exhaustively for any other `setInterval` or `requestAnimationFrame` that modifies `#subtitle-overlay` based on time elapsed, as our current fix inside `playNextBeat` gets overwritten.
