# V3 Player & Pipeline Fixes Changelog

Here is the complete list of fixes and improvements applied to the V3 pipeline and player.

## Player Updates (`player/player_v3.html` & `player/dashboard.html`)

1. **Play/Pause Synchronization (Fix 1)**
   - Added a global `G_PLAYBACK_INTENDED` flag to track whether the user explicitly paused the video.
   - Updated `togglePlayPause()` to toggle this flag.
   - Added guards (`if (!G_PLAYBACK_INTENDED) return;`) to the `_stallCheck`, `_startCheck`, and `_syncInt` interval loops.
   - **Result:** The player no longer automatically resumes playing a paused video when the stall-healer checks fire.

2. **Subtitle Visibility / Teleprompter Mode (Fix 2)**
   - Updated the CSS for `.sub-word`. All upcoming words are now hidden (`display: none`) by default.
   - Only spoken (`.spoken`) and currently active (`.active`) words are shown (`display: inline`).
   - **Result:** Creates a proper teleprompter effect where future words remain hidden until spoken.

3. **Subtitle Karaoke Pause (Fix 7)**
   - Added a pause check inside the `_karaokeTimer` loop.
   - If the avatar video is paused, the timer skips advancing to the next word.
   - **Result:** Subtitles no longer desync and run ahead if the user pauses the video mid-sentence.

4. **Memory Slide Auto-Driver (Fix 3)**
   - Implemented `initMemorySection(sec)` which polls `avVid.currentTime`.
   - Automatically calls `nextCard()` when the avatar playback crosses the duration thresholds of the narration segments.
   - **Result:** Flashcards in the Memory section now automatically flip and advance in sync with the avatar's narration.

5. **Image Fallback Logic (Fix 4)**
   - Added `safeLoadImage(imgEl, baseUrl)` helper to sequentially attempt loading `.png`, `.jpg`, and `.jpeg` extensions using the `onerror` event.
   - Updated `switchToBeat()` to use this helper for infographic images.
   - **Result:** The player gracefully recovers if an image was expected as a `.png` but actually saved as a `.jpg`.

6. **Dashboard Subject and Grade Inputs (Fix 5)**
   - Changed the `subject` and `grade` fields in `dashboard.html` from `type="hidden"` to `type="text"`.
   - **Result:** Users can now manually enter the Subject and Grade on the dashboard instead of relying on the hardcoded defaults.

---

## Pipeline & Prompt Updates

7. **Intro Prompt Template (Fix 6)**
   - Updated the Intro section instruction in `core/prompts/director_global_prompt.txt`.
   - The start phrase now explicitly forces the use of `{{subject}}` and `{{grade}}` placeholder variables.
   - **Result:** Prevents the LLM from hallucinating topics in the intro and ensures the correct dashboard inputs are injected.

8. **Recap Prompt & Logic Correction**
   - Added a strict rule to `core/prompts/director_v3_partition_prompt.txt` mandating that RECAP sections must ALWAYS use the `image_to_video` renderer.
   - Updated `core/partition_director_generator.py` to unconditionally force `render_spec.renderer = "image_to_video"` for Recap sections, automatically converting any incorrectly generated `video_prompts` into `image_to_video_beats`.
   - **Result:** Recap sections successfully and reliably generate images and videos instead of failing with text-to-video errors.

9. **Image Format Detection & Saving**
   - Updated `render/image/image_generator.py` to read the magic bytes of API image responses to detect the actual format (JPEG, PNG, WebP).
   - Added a `_save_image` helper to ensure files are saved with the correct extension matching their underlying data, instead of blindly saving everything as `.png`.
   - **Result:** Prevents broken images caused by saving JPEG bytes into files with a `.png` extension.

10. **Visual Prompt Enhancer — Phase 2.5 (NEW)**
    - Created `core/prompts/visual_prompt_enhancer_prompt.txt` — the system prompt that defines visual style, composition rules, concept alignment, and output format.
    - Created `core/agents/visual_prompt_enhancer.py` — calls GPT-4o (via OpenRouter) once per eligible section to rewrite `image_prompt_start`, `image_prompt_end`, and `video_prompt` fields with high-quality, style-consistent prompts.
    - Modified `core/pipeline_v3.py` — added **Phase 2.5** between the Validator (Phase 2) and Duration Estimation (Phase 3).
    - **Only runs for:** `image_to_video`, `image`, `infographic`. Skipped for `manim`, `none`, `per_question`.
    - **Skipped** automatically in `dry_run` mode (no API cost on test runs).
    - Non-fatal: any per-section error is logged and skipped; the pipeline continues.
    - **Result:** All image-based sections get cinematic, concept-aligned, minimal-style visual prompts before images are generated — consistent across Biology, Math, Pharma, and any subject.

11. **Prompt Enhancer Recap Writeback Fix**
    - **Issue:** GPT-4o frequently stripped the `recap_beat_` prefix, returning just `beat_id: "1"`. This caused the script to fail matching and silently drop the enhanced recap prompts.
    - **Fix:** Switched `apply_enhanced_prompts()` in `visual_prompt_enhancer.py` to use **position-based matching (zip)** instead of `beat_id` string matching. Also added a strict structural rule to the system prompt.
    - **Result:** Recap visuals are now successfully and reliably enhanced.

12. **Player Infographic Merge for `image_to_video` Sections**
    - **Issue:** PDF source images (`infographic_beats`) were not overlaid during `image_to_video` sections because the player only merged them in `loadManimScene`, not `loadVideoScene`.
    - **Fix:** Added the `infographic_beats` merger loop into `loadVideoScene()` inside `player_v3.html` to override the video schedule with image entries.
    - **Result:** Real source images (diagrams, tables, graphs) from the PDF now correctly display in the player during WAN video sections.

13. **Image Source Extension Normalizer (Phase 1.5)**
    - **Issue:** The LLM copied `_img.jpg` filenames from the markdown into `image_source`, but `image_processor.py` saves them as `.png` files. This caused 404s in the player.
    - **Fix:** Added **Phase 1.5** to `pipeline_v3.py`. It scans all `image_source` fields and replaces any `.jpg` extensions with the actual `.png` filenames found on disk using stem-based matching. Also fixed the dict key in `image_processor.py`.
    - **Result:** `presentation.json` exactly matches the filenames generated on disk, eliminating broken image links.

14. **Enhancer Dry Run Override**
    - **Fix:** Removed the `if not dry_run:` gate from Phase 2.5 in `pipeline_v3.py`.
    - **Result:** The Visual Prompt Enhancer now always runs on every job, guaranteeing high-quality cinematic prompts even during dashboard test generation runs.
15. **Image Path Normalization (IMG-002)**
    - **Fix:** Removed the `saved_images` gate in `pipeline_v3.py`. Expanded `_fix_image_source` to scan both `images/` and `generated_images/` directories and strip absolute prefixes. Updated `image_generator.py` to return relative paths.
    - **Result:** Every job (even non-PDF) now gets correct relative paths in `presentation.json`, eliminating 404 errors.

16. **Narrator Placeholder Substitution (SUBST-001)**
    - **Fix:** Implementation of `substitute_placeholders()` in `pipeline_v3.py`.
    - **Process:** Placeholders like `{{subject}}` and `{{grade}}` are now replaced in the narration JSON *before* it is sent to the avatar/TTS generator.
    - **Result:** The avatar now speaks the actual subject and grade instead of literal placeholder brackets.

17. **Summary Bullet Synchronization (SUMM-01)**
    - **Fix:** Rewrote `initSummarySection` in `player_v3.html` to use a `timeupdate` listener on the avatar video.
    - **Result:** Learning objective bullets now reveal exactly when the avatar speaks them, instead of using hardcoded intervals.

18. **Summary Intro Bullet Filter (SUMM-02)**
    - **Fix:** Updated `buildSummaryHTML` to filter out segments with `purpose: "introduce"`.
    - **Result:** The "intro" sentence is no longer rendered as a redundant first bullet point.

19. **Quiz Explanation Visibility (QUIZ-EXP)**
    - **Fix:** Granularly dimmed the quiz UI during explanation videos (Overlay background 0.4, Card background 0.45, Options opacity 0.55).
    - **Result:** The explanation video playing behind the quiz is now clearly visible to the student while keeping the text legible.
