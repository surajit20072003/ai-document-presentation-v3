# Issue Tracker

## Active Issues

### ISS-161: WAN Video Prompts Lost (5 → 1)
**Status**: Open  
**Discovered**: 2024-12-26  
**Severity**: Critical  

**Problem**: Recap section's 5 video_prompts are being concatenated into one 3551-char prompt, which gets truncated to 800 chars, resulting in only 1 video being generated instead of 5.

**Root Cause**: Pipeline mismatch in `wan_runner.py`:
1. RecapAgent outputs `video_prompts: [5 beats]` (649-740 chars each, within limits)
2. `renderer_executor.py` concatenates them into `compiled_wan_prompt` 
3. `wan_runner.py` line 64 checks for `recap_scenes` (empty!) and skips multi-scene mode
4. Falls through to single-prompt mode → 3551 chars → truncated to 800 chars

**Expected Behavior**: 5 separate kie.ai API calls, each with ~700 char prompt, generating 5 videos

**Files Affected**:
- `render/wan/wan_runner.py` - needs to handle `video_prompts` for recap sections
- `core/renderer_executor.py` - concatenation logic

**Fix**: Add handling for recap sections with `video_prompts` (not just `recap_scenes`)

---

### ISS-162: Content Sections Have segments:0
**Status**: RESOLVED (False Positive)  
**Discovered**: 2024-12-26  
**Resolved**: 2024-12-26  
**Severity**: N/A  

**Problem**: Initially appeared that content sections had `segments: 0`.

**Resolution**: This was a FALSE POSITIVE. Segments ARE correctly populated:
- `section.segments` = 0 (section-level field, DEPRECATED/unused)
- `section.narration.segments` = 8 ✅ (CORRECT location per v1.3 schema)

**Evidence**:
```json
{
  "section_type": "content",
  "visual_beats": [8 beats],
  "narration": {
    "full_text": "...",
    "segments": [8 segments with visual_content, display_directives] // CORRECT!
  }
}
```

**Note**: Player must read from `section.narration.segments`, not `section.segments`.

---

### ISS-163: kie.ai Internal Error (topic_10.mp4)
**Status**: Open  
**Discovered**: 2024-12-26  
**Severity**: Medium  

**Problem**: kie.ai returned "internal error" for recap video, but code reported "Success". The resulting topic_10.mp4 is only 14KB (should be 500KB-1MB).

**Evidence**:
```
Runway generation failed: internal error, please try again later.
  -> Success: /home/runner/workspace/player/jobs/fb4d4d7a/videos/topic_10.mp4
```

**Root Cause**: Error handling in WAN client not properly detecting API failures

**Files Affected**:
- `render/wan/wan_client.py` - error handling

---

### ISS-164: Content Fidelity Loss - LLM Modifying Source Content
**Status**: Fixed  
**Discovered**: 2024-12-26  
**Fixed**: 2024-12-26  
**Severity**: Critical  

**Problem**: The visual_content displayed to users contains LLM-generated summaries, NOT the verbatim PDF content.

**Evidence**:
| Stage | Content |
|-------|---------|
| Source PDF | `SinA = $\frac{BC}{AC}$` (with LaTeX, specific triangle values) |
| Chunker | ✅ `$\frac{BC}{AC}$` (verbatim preserved) |
| Presentation.json | ❌ `SinA = Opposite/Hypotenuse` (generic summary, no LaTeX) |

**Root Cause**: VisualSpecArtist agent is generating summaries instead of using `verbatim_content` from chunker blocks.

**Expected Behavior**: 
- `visual_content` should contain EXACT text from PDF
- LaTeX formulas like `$\frac{BC}{AC}$` should be preserved
- No LLM interpretation or simplification

**User Requirement**: "Display as-is" - show actual PDF content, not LLM-generated summaries

**Files to Fix**:
- `core/agents/visual_spec_artist.py` - needs to pass through verbatim_content
- `core/prompts/visual_spec_artist_user_v1.5.txt` - prompt must instruct verbatim usage

**Fix Strategy**:
1. Block ID threading already implemented (ISS-160)
2. Need to use `verbatim_content` from content_blocks instead of LLM summaries
3. Post-processor `_enhance_visual_content_types()` should pull verbatim_content by block_id

---

## Resolved Issues

(None yet)
