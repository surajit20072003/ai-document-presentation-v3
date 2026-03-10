# AI Animated Education

## Overview
This project is a **Deterministic Educational Film Engine** designed to convert PDF chapters into pedagogically structured, animated explanation videos with synchronized narration. Its core purpose is to automate the creation of high-quality, engaging educational content by leveraging AI-driven animation and narration to enhance learning, with ambitions to revolutionize educational content creation and distribution.

## User Preferences
The user wants an iterative development process. The agent should prioritize clear, concise, and accurate communication. Before making any major architectural changes or introducing new dependencies, the agent must ask for explicit approval. The user prefers detailed explanations for complex technical decisions. The agent should ensure that all code is well-documented and follows best practices for maintainability and readability.

## System Architecture
The system operates on **V1.5-V2 Pipeline** (FINAL PRODUCTION VERSION - December 2025).

### V1.5-V2 Pipeline (CURRENT - Single LLM Call Architecture)
The V2 evolution achieves 95% reduction in LLM calls while adding intelligent video generation:

**Key Features:**
- **Single LLM Call**: Entire presentation generated in one API call (~150s)
- **Intelligent Video Examples**: LLM decides when to generate videos per topic (Biology→WAN, Math→Manim)
- **EXPLAIN → SHOW Pattern**: Each topic has explanation segments followed by video examples
- **Decision Logging**: All LLM decisions captured in `decision_log` for analysis
- **Image Workflow**: Datalab extracts PDF images → green screen processing → saved to job/images/
- **Two-Channel Separation**: `display_text` (PDF content on screen) ≠ `segment.text` (TTS narration)

**Pipeline Flow:**
`PDF Upload` → `Datalab (markdown + images)` → `V2 Unified Generator (single LLM)` → `Transform to Player Schema` → `presentation.json`

**Subject-Based Renderer Selection:**
| Subject | Renderer | Use Case |
|---------|----------|----------|
| Biology | video (WAN) | Anatomy, processes, organisms |
| Physics | video/manim | Phenomena (video), equations (manim) |
| Math | manim | Equations, graphs, geometry |
| Chemistry | video/manim | Reactions (video), formulas (manim) |

**API Usage:**
```
POST /submit_job
  - pipeline_version: "v15_v2" (uses V2)
  - pipeline_version: "v15" (uses legacy multi-agent)
```

### Core Architectural Principles
- **PLAYER IS DUMB**: The player executes JSON instructions without determining layout, timing, or pedagogy.
- **ONE PRIMARY ATTENTION LAYER AT A TIME**: Text or visuals are prominent, not both.
- **TEACH → THEN SHOW**: Narration explains, then visuals reinforce.
- **EVERYTHING IS TIMED**: All segments have precise, synchronized durations.
- **TWO-CHANNEL SEPARATION**: Narration is audio-only; `visual_content` is screen display only.
- **Fail-Fast Policy**: Strict fail-fast behavior with no fallbacks for critical components.

### V1.5 Optimized Pipeline
The core process is orchestrated through an optimized series of specialized agents designed to reduce LLM calls:
`Chunker` → `SectionPlanner` → `[per-section: ContentCreator → RendererSpec]` → `SpecialSectionsAgent` → `MergeStep` → `TTS||ManimCodeGen` → `Renderers`

- **ContentCreator**: Combines NarrationWriter and VisualSpecArtist functionalities.
- **SpecialSectionsAgent**: Combines MemoryAgent and RecapAgent functionalities.
- **Parallel Execution**: TTS generation runs in parallel with Manim code generation.
- **Auto-Batching**: Handles large content to prevent token limit truncation errors by estimating content density and processing in batches.
- **Dynamic Budgeting (V1.5.1)**: SectionPlanner calculates per-section word/segment budgets based on SmartChunker's qa_pair_count and concept_count. ContentCreator validates against these dynamic budgets instead of fixed limits. Quiz sections auto-split (1-8 Q&A = 1 section, 9-16 = 2 sections).

### Guardrails
- **Presentation Schema Immutability**: Validation against v1.3 schema.
- **Player Code Freeze**: No changes to the `player/` directory.
- **Two-Channel Separation**: `narration.text` must not equal `visual_content`.
- **Display Directive Mutual Exclusion**: `text_layer` and `visual_layer` cannot both be 'show'.
- **Idempotent Agent Retries**: Agents are pure functions to ensure consistent retries.

### UI/UX Decisions
- **Layer Architecture**: Layer 0 (Background), Layer 1 (Content), Layer 2 (Avatar - always visible).
- **Player V2**: A complete rewrite supporting 7 section types (intro, summary, content, example, quiz, memory, recap), chroma keying for avatar, progressive text reveal, and dynamic content scaling.
- **Header**: Features a "Simple Lecture" logo and dynamic section title.
- **Content Layer**: 70% width, no borders.
- **Avatar Layer**: 55% width, 85% height, floating right, always visible.
- **Video Layer**: 65% width, hides content during playback.
- **LaTeX/MathJax**: Rendering with placeholder preservation.
- **Image Display**: Styled support for images with captions.

### Key System Specifications
- **Display Requirements**: Detailed specifications for display, layer architecture, and section types are defined.
- **V1.5 Requirements**: Covers phases, requirements, agent contracts, JSON schemas, and guardrails.
- **Manim Code Generation**: Claude Sonnet 4.5 is used for Python code output and validation.
- **WAN Video Sync**: Max 15-second duration, narration-driven, with video looping for longer narrations.
- **Document Processing**: Supports multi-format document upload (PDF, DOC, DOCX, ODT) and extracts page counts, Q&A pairs, tables, and images for analytics.

## External Dependencies
-   **OpenRouter**: Provides access to various LLM models (Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Sonnet).
-   **Edge TTS**: Default Text-to-Speech service.
-   **Narakeet API**: Fallback for Text-to-Speech.
-   **Kie.ai API (WAN)**: Used for video generation.
-   **Datalab API**: Handles PDF to Markdown conversion.
-   **Flask/Flask-CORS**: Python web framework.
-   **Mutagen**: Library for measuring audio duration.
-   **MoviePy**: Used for video editing.
-   **Renderers**: Manim, Remotion, and WAN (Kie.ai).