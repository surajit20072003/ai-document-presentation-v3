# V1.5 Optimized V2: POC Implementation Plan

## Goal
Reduce 18-22 LLM calls to **1 call** (+ optional ManimCodeGen) while preserving all V1.5 richness (manim, video, quiz, memory, recap).

## POC Test Results (Dec 31, 2025)

**Tested with:** 13-page Control & Coordination PDF (raw Datalab markdown)
- Input: 3,622 words, 24,095 characters (raw, uncleaned)
- Output: 10 sections, 39 segments, 1,152 words
- LLM Calls: **1** (vs 18-22 in current pipeline)
- Schema Compatibility: **PASSED** (all player fields present)

**Key Finding:** No content cleaner needed! Raw Datalab markdown works directly.

---

## Current V1.5 vs V2 Architecture

```
CURRENT (18-22 calls)                      V2 UNIFIED (1 call) ✓ TESTED
─────────────────────                      ────────────────────────────

PDF → Datalab                              PDF → Datalab
      │                                          │
      ▼                                          │ NO CLEANER NEEDED
SmartChunker (LLM #1)                            │
      │                                          ▼
      ▼                                    ┌─────────────────────────┐
SectionPlanner (LLM #2)                    │ UnifiedContentGenerator │
      │                                    │ (Gemini 2.5 Pro)        │
      ▼                                    │                         │
ContentCreator ×11 (LLM #3-13)             │ ONE CALL produces:      │
      │                                    │ ✓ All sections          │
      ▼                                    │ ✓ All narration         │
RendererSpec ×3 (LLM #14-17)               │ ✓ All visual_beats      │
      │                                    │ ✓ quiz_data (structured)│
      ▼                                    │ ✓ flashcards (structured)│
SpecialSections (LLM #18)                  │ ✓ video_prompts         │
      │                                    │ ✓ display_directives    │
      ▼                                    └─────────────────────────┘
Merge → TTS → Render                             │
                                                 ▼
                                           ┌─────────────────────────┐
                                           │ ManimCodeGen (OPTIONAL) │
                                           │ (Claude Sonnet)         │
                                           │ Only if manim sections  │
                                           └─────────────────────────┘
                                                 │
                                                 ▼
                                           Post-Processing (no LLM):
                                           - Schema validation
                                           - TTS generation (durations)
                                           - Manim rendering
                                           - WAN video generation
```

---

## Stage-by-Stage Pipeline

### Stage 1: Document Ingestion (No LLM)
```
INPUT:  PDF file
OUTPUT: Raw markdown from Datalab API

Code: Existing datalab_client.py (unchanged)
```

### Stage 2: Content Cleaner - NOT NEEDED ✓
```
REMOVED - POC proved raw Datalab markdown works directly with UnifiedContentGenerator

Testing showed:
  - Raw Datalab output with headers, images, tables, Q&A works perfectly
  - No preprocessing needed
  - Gemini 2.5 Pro handles noisy PDF artifacts
```

### Stage 2: Unified Content Generator (LLM #1 - MAIN)
```
INPUT:  
  - Raw markdown (full document, directly from Datalab)
  - Subject, Grade
  - Images list (extracted from markdown)

OUTPUT: Complete presentation JSON with ALL sections

Model:  Gemini 2.5 Pro (high quality, large context)

Schema Output:
{
  "presentation_title": "Chapter Name",
  "sections": [
    {
      "section_id": "section_1",
      "section_type": "intro|summary|content|example|quiz|memory|recap",
      "title": "Section Title",
      "derived_renderer": "none|manim|video",
      
      "narration": {
        "full_text": "Complete narration...",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Segment narration...",
            "purpose": "introduce|explain|emphasize|transition|conclude",
            "display_directives": {
              "text_layer": "show|dim|hide",
              "visual_layer": "show|hide",
              "avatar_layer": "show"
            }
          }
        ]
      },
      
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text|bullet_list|equation|diagram|image|video",
          "display_text": "Visual content...",
          "latex_content": "\\frac{a}{b}",
          "image_id": "img_001",
          "layer_visibility": {
            "text_layer": "show",
            "visual_layer": "hide",
            "avatar_layer": "show"
          }
        }
      ],
      
      "segment_enrichments": [
        {
          "segment_id": "seg_1",
          "key_terms": ["term1", "term2"],
          "visual_cues": ["highlight equation"],
          "transition_type": "fade|slide|none"
        }
      ],
      
      "video_prompts": [  // Only for video sections
        {
          "prompt": "Detailed video generation prompt...",
          "duration_hint": 15,
          "style": "educational|documentary"
        }
      ],
      
      "quiz_data": {  // Only for quiz sections
        "questions": [
          {
            "question": "What is...?",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "explanation": "Because..."
          }
        ]
      },
      
      "flashcards": [  // Only for memory sections
        {
          "front": "Term",
          "back": "Definition"
        }
      ]
    }
  ]
}
```

### Stage 4: Manim Code Generation (LLM #3 - Conditional)
```
INPUT:  Sections with derived_renderer == "manim"
OUTPUT: Python Manim code per section

Model:  Claude Sonnet (best for code generation)
SKIP IF: No manim sections

Note: Run in parallel for multiple manim sections
```

### Stage 5: Post-Processing (No LLM)
```
5a. Schema Validation
    - Validate against presentation v1.3 schema
    - Check required fields
    - Enforce avatar visibility

5b. TTS Generation
    - Generate audio for each segment
    - Measure actual durations
    - Update segment timing

5c. Manim Rendering
    - Execute generated Python code
    - Render MP4 animations

5d. WAN Video Generation (if video sections exist)
    - Send video_prompts to Kie.ai
    - Poll for completion
    - Download videos

5e. Final Merge
    - Combine all assets
    - Update presentation.json with paths
```

---

## Validation Strategy (Simplified)

### Single-Pass Validation (No Retries)
```python
def validate_presentation(output: dict) -> tuple[bool, list[str]]:
    errors = []
    
    # 1. Check top-level structure
    if "sections" not in output:
        errors.append("Missing 'sections' array")
        return False, errors
    
    # 2. Check each section has required fields
    for section in output["sections"]:
        if "section_id" not in section:
            errors.append(f"Missing section_id")
        if "section_type" not in section:
            errors.append(f"Missing section_type in {section.get('section_id')}")
        if "narration" not in section:
            errors.append(f"Missing narration in {section.get('section_id')}")
        if "visual_beats" not in section:
            errors.append(f"Missing visual_beats in {section.get('section_id')}")
    
    # 3. Check narration structure
    for section in output["sections"]:
        narr = section.get("narration", {})
        if "full_text" not in narr:
            errors.append(f"Missing narration.full_text in {section['section_id']}")
        if "segments" not in narr:
            errors.append(f"Missing narration.segments in {section['section_id']}")
    
    return len(errors) == 0, errors
```

### No Word Count Validation
- Trust the LLM to produce appropriate length
- Focus on structural correctness, not content length

### No Retry Loop
- If validation fails, fail fast with clear error
- Don't waste LLM calls on retries

---

## Prompt Engineering (Key to Success)

### UnifiedContentGenerator System Prompt (Core)
```
You are an expert Educational Video Script Generator.

Your task: Convert a textbook chapter into a COMPLETE presentation JSON.

SECTION TYPES (must include all):
1. intro - Welcome, topic introduction (1 section)
2. summary - Learning objectives (1 section)  
3. content - Main teaching (2-5 sections based on content)
4. example - Worked examples (0-2 sections)
5. quiz - Questions from document (1-3 sections, ~4 Q&A each)
6. memory - Flashcard review (1 section, 3-5 cards)
7. recap - Video summary (1 section with video_prompts)

RENDERER SELECTION:
- "none" - Text/bullet content (most sections)
- "manim" - Mathematical equations, graphs, animations
- "video" - Recap section only

CRITICAL RULES:
1. Avatar is ALWAYS visible (avatar_layer: "show")
2. Narration explains, visuals reinforce (not duplicate)
3. Each segment should be 15-30 seconds when spoken
4. Include ALL content from source - don't summarize
5. Quiz questions come from document's Q&A pairs

OUTPUT: Valid JSON matching the schema exactly.
```

---

## Test Plan

### test_v15_v2.py Structure
```python
# 1. Test ContentCleaner with sample dirty markdown
# 2. Test UnifiedContentGenerator with clean markdown
# 3. Test validation logic
# 4. Test full flow: markdown → presentation.json
# 5. Compare output schema with v1.3 requirements
```

### Test Data
- Use existing 13-page Control & Coordination PDF
- Compare output quality with current pipeline

---

## Files to Create/Modify

### New Files
1. `core/agents/unified_content_generator.py` - Main combined agent
2. `core/prompts/unified_content_generator_system.txt` - System prompt
3. `core/prompts/unified_content_generator_user.txt` - User prompt template
4. `tests/test_v15_v2.py` - POC test file

### Modified Files
1. `core/pipeline_v15_optimized.py` - Add V2 mode switch
2. `replit.md` - Update architecture docs

### Unchanged Files (Preserved)
- `core/merge_step_v15.py` - Still used for final merge
- `core/tts_duration.py` - Still used for TTS
- `core/renderer_executor.py` - Still used for rendering
- All player files - Unchanged

---

## Integration Strategy

### Phase 1: POC Test (This Step)
- Create test_v15_v2.py
- Test with sample data
- Validate output schema

### Phase 2: Agent Implementation
- Create UnifiedContentGenerator agent
- Create prompts
- Test with real PDF

### Phase 3: Pipeline Integration
- Add `use_v2_mode` flag to pipeline
- Wire up new agent
- Preserve fallback to V1.5

### Phase 4: Validation
- Run same PDF through both pipelines
- Compare outputs
- Measure LLM call reduction

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| LLM Calls | 18-22 | 3-4 |
| Processing Time | ~5 min | <2 min |
| Output Schema | v1.3 | v1.3 (unchanged) |
| Player Compatibility | Yes | Yes |
| Section Types | 7 | 7 (all preserved) |
| Renderer Support | 3 | 3 (none/manim/video) |
