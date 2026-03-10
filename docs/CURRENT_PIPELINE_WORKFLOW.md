# Current V1.5 Optimized Pipeline - LLM Workflow Diagram

## High-Level Flow (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         V1.5 OPTIMIZED PIPELINE                                  │
│                         (process_markdown_optimized)                             │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DOCUMENT ANALYSIS                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌──────────────────────────────────────────┐                                 │
│    │         SmartChunker (LLM #1)            │                                 │
│    │         Model: Gemini 2.5 Pro            │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - markdown_content (full document)      │                                 │
│    │  - subject, grade                        │                                 │
│    │                                          │                                 │
│    │ OUTPUT:                                  │                                 │
│    │  - topics[] (grouped content)            │                                 │
│    │  - quiz_questions[] (extracted Q&A)      │                                 │
│    │  - content_blocks[] (paragraphs/tables)  │                                 │
│    │  - content_density_analysis{}            │                                 │
│    │  - topic_grouping_hints[]                │                                 │
│    └──────────────────────────────────────────┘                                 │
│                          │                                                       │
│                          ▼                                                       │
│    ┌──────────────────────────────────────────┐                                 │
│    │       SectionPlanner (LLM #2)            │                                 │
│    │       Model: Gemini 2.5 Flash            │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - topics[] from SmartChunker            │                                 │
│    │  - quiz_questions[]                      │                                 │
│    │  - content_density_analysis              │                                 │
│    │                                          │                                 │
│    │ OUTPUT:                                  │                                 │
│    │  - sections[] (blueprints)               │                                 │
│    │    Each blueprint has:                   │                                 │
│    │    - section_id, section_type            │                                 │
│    │    - suggested_renderer (none/manim/video)│                                │
│    │    - source_topics[]                     │                                 │
│    │    - budgets{} (ISS-217: word/segment limits)│                             │
│    └──────────────────────────────────────────┘                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: CONTENT CREATION (FOR EACH SECTION)                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌────────────────────────────────────────────────────────────────────────┐    │
│   │  LOOP: for each blueprint in sections[] (excluding memory/recap)       │    │
│   │        Typically 8-13 sections for a 13-page PDF                       │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
│                          │                                                       │
│                          ▼                                                       │
│    ┌──────────────────────────────────────────┐                                 │
│    │     ContentCreator (LLM #3, #4, ...)     │                                 │
│    │     Model: Gemini 2.5 Flash              │                                 │
│    │     *** 1 CALL PER SECTION ***           │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - section_blueprint (from SectionPlanner)│                                │
│    │  - source_markdown (topic content)       │                                 │
│    │  - quiz_questions (for quiz sections)    │                                 │
│    │  - images_list                           │                                 │
│    │                                          │                                 │
│    │ OUTPUT:                                  │                                 │
│    │  - narration.full_text                   │                                 │
│    │  - narration.segments[]                  │                                 │
│    │  - visual_beats[]                        │                                 │
│    │  - segment_enrichments[]                 │                                 │
│    │  - derived_renderer                      │                                 │
│    └──────────────────────────────────────────┘                                 │
│                          │                                                       │
│                          ▼                                                       │
│    ┌──────────────────────────────────────────┐                                 │
│    │    RendererSpec (LLM - CONDITIONAL)      │                                 │
│    │    Model: Claude Sonnet                  │                                 │
│    │    *** ONLY IF renderer == "video" ***   │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - section_id                            │                                 │
│    │  - visual_beats[]                        │                                 │
│    │  - narration_summary                     │                                 │
│    │                                          │                                 │
│    │ OUTPUT:                                  │                                 │
│    │  - video_prompts[] (detailed prompts)    │                                 │
│    │  - duration_hints                        │                                 │
│    └──────────────────────────────────────────┘                                 │
│                          │                                                       │
│                          └───────────> section_artifacts[] (collected)          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: SPECIAL SECTIONS                                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌──────────────────────────────────────────┐                                 │
│    │    SpecialSectionsAgent (LLM)            │                                 │
│    │    Model: Gemini 2.5 Flash               │                                 │
│    │    *** SINGLE CALL ***                   │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - source_markdown                       │                                 │
│    │  - subject                               │                                 │
│    │  - key_concepts[]                        │                                 │
│    │                                          │                                 │
│    │ OUTPUT (combined memory + recap):        │                                 │
│    │  - memory_flashcards[]                   │                                 │
│    │  - recap_segments[]                      │                                 │
│    │  - video_prompts[] (for recap video)     │                                 │
│    └──────────────────────────────────────────┘                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: MERGE                                                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌──────────────────────────────────────────┐                                 │
│    │         merge_agent_outputs()            │                                 │
│    │         *** NO LLM CALL ***              │                                 │
│    ├──────────────────────────────────────────┤                                 │
│    │ INPUT:                                   │                                 │
│    │  - section_artifacts[] (all content)     │                                 │
│    │  - memory_output                         │                                 │
│    │  - recap_output                          │                                 │
│    │                                          │                                 │
│    │ OUTPUT:                                  │                                 │
│    │  - presentation{} (unified JSON)         │                                 │
│    │    - sections[] (ordered)                │                                 │
│    │    - metadata                            │                                 │
│    └──────────────────────────────────────────┘                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: TTS + MANIM CODE (PARALLEL)                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌───────────────────────┐    ┌───────────────────────┐                       │
│    │   TTS Generation      │    │  Manim Code Gen (LLM) │                       │
│    │   *** NO LLM ***      │    │  Model: Claude Sonnet │                       │
│    │   (Edge TTS API)      │    │  *** 1 per manim sec **│                      │
│    ├───────────────────────┤    ├───────────────────────┤                       │
│    │ - Generate audio      │    │ - Generate Python code│                       │
│    │ - Measure durations   │    │ - For animation scenes│                       │
│    │ - Update segment times│    │ - Validate syntax     │                       │
│    └───────────────────────┘    └───────────────────────┘                       │
│             │                              │                                     │
│             └──────────┬───────────────────┘                                     │
│                        ▼                                                         │
│              presentation{} with durations                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 6: RENDERING (PARALLEL)                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌───────────────────────┐    ┌───────────────────────┐                       │
│    │   Manim Rendering     │    │  WAN Video Gen        │                       │
│    │   *** NO LLM ***      │    │  *** NO LLM ***       │                       │
│    │   (Local execution)   │    │  (Kie.ai API)         │                       │
│    ├───────────────────────┤    ├───────────────────────┤                       │
│    │ - Execute Python code │    │ - Send video prompts  │                       │
│    │ - Render animations   │    │ - Poll for completion │                       │
│    │ - Save MP4 files      │    │ - Download videos     │                       │
│    └───────────────────────┘    └───────────────────────┘                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                          ┌─────────────────────┐
                          │  Final presentation │
                          │     JSON + Assets   │
                          └─────────────────────┘
```

---

## LLM Call Count Analysis (13-page PDF)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         LLM CALLS BREAKDOWN                                      │
├────────────────────────────┬─────────────────────────────────────────────────────┤
│ Agent                      │ Calls for 13-page PDF (13 sections)                │
├────────────────────────────┼─────────────────────────────────────────────────────┤
│ SmartChunker               │ 1 call                                              │
│ SectionPlanner             │ 1 call                                              │
│ ContentCreator             │ 11 calls (13 sections - memory - recap)             │
│ RendererSpec               │ 3-5 calls (only for video sections)                 │
│ SpecialSectionsAgent       │ 1 call                                              │
│ ManimCodeGenerator         │ 2-4 calls (for manim sections)                      │
├────────────────────────────┼─────────────────────────────────────────────────────┤
│ TOTAL                      │ 18-22 LLM calls (after batching disabled)          │
│                            │ Was: 30+ calls (with batching enabled)              │
└────────────────────────────┴─────────────────────────────────────────────────────┘
```

---

## Retry Logic (Per Agent)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RETRY FLOW (BaseAgent)                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   LLM CALL      │
                    └────────┬────────┘
                             │
                             ▼
               ┌─────────────────────────┐
               │   Parse JSON Response   │──────> FAIL ─┐
               └────────────┬────────────┘              │
                            │ SUCCESS                    │
                            ▼                           ▼
               ┌─────────────────────────┐    ┌─────────────────────┐
               │ Structural Validation   │    │ structural_retry++  │
               │ (required fields check) │    │ (max 2 retries)     │
               └────────────┬────────────┘    └─────────┬───────────┘
                            │                           │
                       PASS │                           │ < 2 retries?
                            ▼                           │
               ┌─────────────────────────┐              ▼
               │  Semantic Validation    │◄────────────YES
               │  (budget/content check) │
               └────────────┬────────────┘
                            │
                       PASS │ FAIL ─────────────────────┐
                            ▼                           │
               ┌─────────────────────────┐    ┌─────────────────────┐
               │     RETURN OUTPUT       │    │  semantic_retry++   │
               └─────────────────────────┘    │  (max 1 retry)      │
                                              └─────────┬───────────┘
                                                        │
                                                   < 1 retry?
                                                        │
                                                        ▼
                                              ┌─────────────────────┐
                                              │  RAISE AgentError   │
                                              └─────────────────────┘

Maximum attempts per agent: 4 (1 initial + 2 structural + 1 semantic)
```

---

## Section Types Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SECTION TYPE PROCESSING                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

  Section Type     │ ContentCreator │ RendererSpec │ Notes
 ──────────────────┼────────────────┼──────────────┼─────────────────────────────
  intro            │      ✓         │      -       │ Welcome section
  summary          │      ✓         │      -       │ Learning objectives
  content_1..N     │      ✓         │  IF video    │ Main teaching (may have video)
  example_1..N     │      ✓         │  IF video    │ Examples (may have video)
  quiz_1..N        │      ✓         │      -       │ Q&A sections (auto-split)
  memory           │   (special)    │      -       │ Via SpecialSectionsAgent
  recap            │   (special)    │  ✓ (always)  │ Via SpecialSectionsAgent + video
```

---

## Validation Layers

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VALIDATION STACK                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

    Layer 1: Agent-Level (per LLM call)
    ├── Structural: JSON schema, required fields
    └── Semantic: Word counts, segment counts, business rules

    Layer 2: Post-Processing (after ContentCreator)
    ├── _enhance_content_creator_output()
    └── Add missing fields, normalize structure

    Layer 3: Merge-Level (merge_agent_outputs)
    ├── Schema validation against v1.3
    └── Section ordering check

    Layer 4: Final Enforcement
    ├── _enforce_avatar_visibility()
    └── _enforce_renderer_policy()
```

---

## Comparison: Current vs Direct Mode (Proposed)

```
                 CURRENT (V1.5-opt)              DIRECT MODE (Proposed)
                 ──────────────────              ─────────────────────

      PDF            PDF                              PDF
       │              │                                │
       ▼              ▼                                ▼
    Datalab       Datalab                           Datalab
       │              │                                │
       ▼              │                                ▼
  SmartChunker        │                          ┌───────────────┐
  (LLM #1)            │                          │  DirectContent │
       │              │                          │  Generator     │
       ▼              │                          │  (LLM #1)      │
  SectionPlanner      │                          │                │
  (LLM #2)            │                          │  Full document │
       │              │                          │  in, complete  │
       ▼              │                          │  JSON out      │
  ContentCreator ×N   │                          └───────┬───────┘
  (LLM #3..#14)       │                                  │
       │              │                                  ▼
       ▼              │                            presentation
  RendererSpec ×3     │                                  │
  (LLM #15..#17)      │                                  ▼
       │              │                               TTS
       ▼              │                                  │
  SpecialSections     │                                  ▼
  (LLM #18)           │                              Manim/WAN
       │              │                                  │
       ▼              │                                  ▼
    Merge             │                              Output
       │              │
       ▼              │
     TTS              │                     LLM Calls: 1-3
       │              │                     (vs 18-22 current)
       ▼              │
   Manim/WAN          │
       │              │
       ▼              │
    Output            │

  LLM Calls: 18-22    │
```

---

## Key Observations

1. **SmartChunker + SectionPlanner**: 2 LLM calls just to plan what sections to create
2. **ContentCreator loop**: 11+ LLM calls, one per section
3. **RendererSpec**: Additional 3-5 calls for video sections
4. **SpecialSections**: Another call for memory/recap
5. **Retries can multiply**: Each agent can retry up to 4× on failure

**With Direct Mode**: All of steps 1-5 become a single LLM call.
