# Direct Mode: Simplified Pipeline for Small Documents

## Goal

Reduce LLM calls from 30+ to **1-3 calls** for small documents (<20 pages) by bypassing the multi-agent pipeline and sending the full document to a single LLM call.

---

## Current vs Direct Mode Comparison

### Current Pipeline (V1.5-opt)
```
PDF (13 pages)
    ↓
[Datalab API] → Markdown
    ↓
[SmartChunker] → 1 LLM call
    ↓
[SectionPlanner] → 1 LLM call
    ↓
[ContentCreator] → 13 sections = 13 LLM calls
    ↓
[RendererSpec] → 3-5 LLM calls
    ↓
[SpecialSections] → 1 LLM call
    ↓
[Merge/Validate]
    ↓
[TTS + Manim]

Total: ~20-30 LLM calls
```

### Direct Mode (Proposed)
```
PDF (13 pages)
    ↓
[Datalab API] → Markdown
    ↓
[DirectContentGenerator] → 1 LLM call (Gemini 2.5 Pro)
    ↓
[TTS + Manim]

Total: 1-3 LLM calls
```

---

## When to Use Direct Mode

| Criteria | Direct Mode | Full Pipeline |
|----------|-------------|---------------|
| Page count | ≤20 pages | >20 pages |
| Q&A pairs | ≤30 | >30 |
| Concepts | ≤50 | >50 |
| Token estimate | <50k tokens | >50k tokens |

Auto-detection at job start:
```python
def should_use_direct_mode(markdown_content: str, page_count: int) -> bool:
    if page_count > 20:
        return False
    token_estimate = len(markdown_content) // 4  # ~4 chars per token
    if token_estimate > 50000:
        return False
    return True
```

---

## Direct Mode Architecture

### Single Agent: DirectContentGenerator

**Input**: Full markdown content + metadata (page_count, title)

**Output**: Complete presentation JSON matching v1.3 schema

**Model**: Gemini 2.5 Pro (large context, high quality)

**Prompt Strategy**: Single comprehensive prompt that includes:
1. Document content (full markdown)
2. Section type instructions (intro, summary, content, quiz, memory, recap)
3. Visual beat generation rules
4. Narration guidelines
5. Output schema

### Prompt Template (Simplified)
```
You are an educational content creator. Convert this textbook chapter into a presentation.

## Document
{full_markdown_content}

## Required Output
Generate a complete presentation with these sections:
1. intro - Brief welcome and topic introduction
2. summary - Key learning objectives (3-5 bullet points)
3. content - Main teaching content (split into logical parts)
4. quiz - Questions from the document (if Q&A pairs exist)
5. memory - 3-5 flashcard-style review items
6. recap - Brief wrap-up

## Output Format
Return a JSON object with this structure:
{
  "presentation_title": "...",
  "sections": [
    {
      "section_id": "section_1",
      "section_type": "intro|summary|content|quiz|memory|recap",
      "derived_renderer": "none|manim|video",
      "narration": {
        "full_text": "Complete narration text...",
        "segments": [
          {"segment_id": "seg_1", "text": "...", "purpose": "..."}
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text|bullet_list|image|video|diagram",
          "display_text": "...",
          "layer_visibility": {"text_layer": "show|dim", "visual_layer": "show|hide", "avatar_layer": "show"}
        }
      ]
    }
  ]
}

Important:
- Avatar layer is always "show"
- Narration explains, visuals reinforce (not duplicate)
- Keep segments 15-30 seconds each
- Generate 8-15 sections total based on content
```

---

## Implementation Plan

### Phase 1: DirectContentGenerator Agent
**Files to create/modify**:
1. `core/agents/direct_content_generator.py` - New agent
2. `core/prompts/direct_content_generator_system.txt` - System prompt
3. `core/prompts/direct_content_generator_user.txt` - User prompt template

**Agent structure**:
```python
class DirectContentGeneratorAgent(BaseAgent):
    agent_name = "DirectContentGenerator"
    model = "google/gemini-2.5-pro-preview"
    structural_retries = 1  # Minimal retries
    semantic_retries = 0    # Trust the output
    
    def validate_structural(self, output):
        # Only check JSON structure, not content lengths
        return has_required_fields(output)
    
    def validate_semantic(self, output, input_data):
        # Skip strict validation - trust large model
        return True, []
```

### Phase 2: Pipeline Integration
**Files to modify**:
1. `core/pipeline_v15_optimized.py` - Add direct mode branch
2. `api/app.py` - Add direct_mode flag to job config

**Logic flow**:
```python
def run_pipeline(job_id, markdown_content, page_count, ...):
    # Auto-detect or use explicit flag
    if should_use_direct_mode(markdown_content, page_count):
        return run_direct_mode(job_id, markdown_content, ...)
    else:
        return run_full_pipeline(job_id, markdown_content, ...)
```

### Phase 3: Direct Mode Runner
**New function in pipeline**:
```python
def run_direct_mode(job_id, markdown_content, title, page_count, ...):
    update_progress(job_id, 10, "Starting direct mode generation")
    
    # Single LLM call
    agent = DirectContentGeneratorAgent()
    result = agent.run(
        markdown_content=markdown_content,
        title=title,
        page_count=page_count
    )
    
    update_progress(job_id, 50, "Content generated")
    
    # Validate against v1.3 schema
    validate_presentation_schema(result)
    
    update_progress(job_id, 60, "Generating audio")
    
    # TTS (same as full pipeline)
    result = update_durations_from_tts(result, ...)
    
    update_progress(job_id, 80, "Rendering visuals")
    
    # Manim/Video rendering (same as full pipeline)
    result = render_all_topics(result, ...)
    
    update_progress(job_id, 100, "Complete")
    return result
```

---

## Validation Strategy (Simplified)

### What to validate:
1. JSON parseable
2. Has `sections` array
3. Each section has required fields (`section_id`, `section_type`, `narration`, `visual_beats`)
4. Schema matches v1.3

### What NOT to validate:
- Word counts (trust the LLM)
- Segment counts (trust the LLM)
- Exact budget adherence (no budgets in direct mode)

---

## Fallback Strategy

If direct mode fails (JSON parse error, schema mismatch):
1. **Option A**: Retry once with explicit schema in prompt
2. **Option B**: Fall back to full pipeline automatically
3. **Option C**: Fail fast with clear error (user preference)

Recommendation: **Option C** - Fail fast. If Gemini 2.5 Pro can't handle a 13-page document in one call, there's a prompt problem, not a need for batching.

---

## Testing Plan

1. **Test with existing 13-page PDF** (Control & Coordination)
   - Verify single LLM call completes
   - Verify output matches v1.3 schema
   - Verify TTS and Manim work with output

2. **Compare outputs**
   - Direct mode vs full pipeline for same document
   - Quality should be similar or better (more context = better coherence)

3. **Edge cases**
   - 1-page document
   - 20-page document (boundary)
   - Document with many images
   - Document with complex equations

---

## Estimated Effort

| Phase | Effort | Files |
|-------|--------|-------|
| Phase 1: Agent | 2-3 hours | 3 new files |
| Phase 2: Pipeline | 1-2 hours | 2 modified files |
| Phase 3: Testing | 1-2 hours | - |
| **Total** | **4-7 hours** | 3 new, 2 modified |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| LLM output too long (token limit) | Use streaming response, chunk if needed |
| JSON parse failures | Include explicit JSON schema in prompt |
| Missing section types | List all required sections explicitly |
| Quality regression | A/B test against full pipeline |

---

## Decision Points for Review

1. **Auto-detect vs explicit flag?**
   - Recommended: Auto-detect with override option

2. **Fallback on failure?**
   - Recommended: Fail fast, don't hide issues

3. **Keep full pipeline code?**
   - Recommended: Yes, for large documents and as fallback

4. **Which model for direct mode?**
   - Recommended: Gemini 2.5 Pro (larger context, better quality)

---

## Summary

Direct Mode reduces complexity by:
- Eliminating 4 intermediate agents (SmartChunker, SectionPlanner, RendererSpec, SpecialSections)
- Removing batching entirely
- Simplifying validation to schema-only
- Trusting modern LLMs to handle full document context

The result: **1 LLM call instead of 30+** for typical educational chapters.
