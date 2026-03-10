# ISS-160: Display Content Fidelity Upgrade Plan

**Created**: 2025-12-26  
**Status**: IN PROGRESS  
**Reference**: docs/llm_requirement.md, docs/display_requirements.md

---

## User Requirements (Confirmed)

### R1: Source Content Preservation
- Display source content **AS-IS** - no LLM modification
- If too many sentences → chunk into next section/slide **without losing context**
- Paragraphs stay as paragraphs, bullets stay as bullets

### R2: Inline LaTeX Handling
- **As-is in source = As-is in display**
- Inline LaTeX `$\sin\theta$` stays inline within paragraph
- Display LaTeX renders same as source placement

### R3: LLM-Driven Timing (No Default Flip)
- If LLM doesn't specify `flip_timing_sec` → **NO FLIP**
- Everything is driven by LLM, no player-side defaults
- Player executes exactly what LLM specifies

---

## Implementation Tasks

| # | Task | Component | Status |
|---|------|-----------|--------|
| 1 | Update docs/llm_requirement.md with block_type and content_type specs | Docs | pending |
| 2 | Update docs/display_requirements.md with paragraph mode, fullscreen video | Docs | pending |
| 3 | Enhance SmartChunker: detect block_type from markdown | Core | pending |
| 4 | Update SectionPlanner: pass block_type metadata | Core | pending |
| 5 | Update VisualSpecArtist schema: content_type, verbatim_text, flip_timing_sec | Core | pending |
| 6 | Update section_visuals.schema.json with new fields | Schema | pending |
| 7 | Update MergeStep: propagate block_type and timing | Core | pending |
| 8 | Update player.js: paragraph renderer, ordered list, fullscreen video, flip timing | Player | pending |
| 9 | End-to-end test with 3-Page Maths PDF | Test | pending |

---

## Technical Design

### SmartChunker Block Detection

```python
def detect_block_type(line: str) -> str:
    stripped = line.strip()
    if re.match(r'^\d+\.\s', stripped):
        return "ordered_list"
    if re.match(r'^[-*+]\s', stripped):
        return "unordered_list"
    if '$' in stripped:
        return "formula"
    if stripped.startswith('>'):
        return "blockquote"
    return "paragraph"
```

### New Chunker Output Schema

```json
{
  "chunks": [
    {
      "block_id": 1,
      "block_type": "paragraph|unordered_list|ordered_list|formula|blockquote",
      "verbatim_content": "Exact source text (NEVER modified)",
      "source_line": 5,
      "items": ["item1", "item2"]  // Only for list types
    }
  ]
}
```

### New VisualContent Schema

```json
{
  "visual_content": {
    "content_type": "paragraph|bullet_list|ordered_list|formula|flashcard|quiz|example_steps",
    "verbatim_text": "Exact source text for paragraphs",
    "bullet_points": [...],
    "ordered_list": ["1. Step one", "2. Step two"],
    "formula": "$\\sin\\theta$",
    "formulas": []
  },
  "display_directives": {
    "text_layer": "show|hide|swap",
    "visual_layer": "show|hide|replace",
    "avatar_layer": "show|gesture_only",
    "flip_timing_sec": null  // null = NO FLIP, LLM must specify
  }
}
```

### Player Flip Logic

```javascript
// Only flip if LLM explicitly specifies timing
const flipAt = segment.display_directives?.flip_timing_sec;
if (flipAt !== null && flipAt !== undefined && elapsedInSegment >= flipAt) {
  showVisualLayer();
  hideTextLayer();
}
// If flipAt is null/undefined → NO automatic flip
```

---

## Validation Checklist

- [ ] SmartChunker outputs block_type for each chunk
- [ ] verbatim_content matches source exactly (byte-for-byte)
- [ ] VisualSpecArtist preserves content_type from chunker
- [ ] Player renders paragraphs as prose (not bullets)
- [ ] Inline LaTeX renders correctly within paragraphs
- [ ] No flip occurs unless LLM specifies flip_timing_sec
- [ ] Fullscreen video when visual_layer="show"

---

## Critical Rule

**LLM output changes → Downstream display MUST update accordingly**

Any new fields added by LLM agents must be:
1. Passed through MergeStep to presentation.json
2. Handled by player.js for rendering
3. Documented in both llm_requirement.md and display_requirements.md
