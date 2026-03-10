# Display Requirements Specification

**Version**: 2.1  
**Last Updated**: 2025-12-24  
**Status**: SINGLE SOURCE OF TRUTH  
**Includes**: Display Requirements, LLM Agents, Manim Implementation, Test Plan  

---

## Table of Contents

1. [Overview](#overview)
2. [Display Summary Table](#display-summary-table)
3. [Layer Architecture](#layer-architecture)
4. [Section Type Layouts (ASCII)](#section-type-layouts-ascii)
5. [LLM Agent Reference](#llm-agent-reference)
6. [Implementation Checklist](#implementation-checklist)
7. [Narration Sync Architecture](#narration-sync-architecture)
8. [Requirement Tracking](#requirement-tracking)
9. [Manim Code Generation](#manim-code-generation)
10. [Test Plan](#test-plan)
11. [Test Input Document](#test-input-document)

---

## Overview

This document defines how the AI Animated Education player displays educational content. It serves as the **SINGLE SOURCE OF TRUTH** for:

- **WHAT** is displayed (text, video, avatar)
- **WHERE** components are positioned (left, right, center)
- **WHEN** transitions occur (timing from narration segments)
- **HOW** the display_directives control layer visibility

### Core Principles

1. **"The Player is DUMB"** - The player executes JSON instructions without making decisions about layout, timing, or pedagogy.
2. **Avatar is ALWAYS VISIBLE** - Layer 2 always renders the avatar. `gesture_only` is metadata for avatar VIDEO GENERATION (lip-sync vs gesture-only), NOT a display hide directive.
3. **P7 Content Integrity** - Display ONLY content from the input source file. No fabricated content.
4. **Narration Sync** - All timing flows from TTS audio duration, which updates segment.duration_seconds.
5. **Source Fidelity (ISS-160)** - Display source content AS-IS: paragraphs as prose, bullets as bullets, numbered lists as numbered.
6. **LLM-Driven Timing (ISS-160)** - Player has NO default timing. If LLM doesn't specify `flip_timing_sec`, NO flip occurs.

---

## Display Summary Table

| Section  | Avatar Position | Avatar Width | Text/Content Area | Video Area | Renderer |
|----------|-----------------|--------------|-------------------|------------|----------|
| **Intro**   | Center       | **60%**      | NONE (avatar-only)| None       | none     |
| **Summary** | Right        | **52%**      | Left 45%          | None       | none     |
| **Content** | Right        | **52%**      | Left 45%          | Fullscreen when playing | manim/video |
| **Example** | Right        | **52%**      | Left 45%          | Fullscreen when playing | manim |
| **Quiz**    | Right        | **52%**      | Left 45%          | None       | none     |
| **Memory**  | Right        | **52%**      | Flashcards        | None       | none     |
| **Recap**   | Right        | **52%**      | None              | Fullscreen | video (WAN) |

### Pixel Specifications (Reference - 1920x1080 viewport)

| Section | Avatar Size | Avatar Position | Content Size | Content Position |
|---------|-------------|-----------------|--------------|------------------|
| **Intro** | 990x557px | R:46px B:1px (center) | 914x502px | L:65px T:70px |
| **Summary/Content/etc** | 1008x567px | R:-245px B:1px (right) | 850x777px | L:41px T:-20px |

**Avatar Aspect Ratio**: 1.78 (16:9)

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LAYER STACK (Z-INDEX)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Layer 2 (Top):    AVATAR VIDEO (always rendered, never hidden)    │
│                     - Position varies by section type               │
│                     - Width: 52% for ALL section types              │
│                     - gesture_only = generation metadata ONLY       │
│                                                                      │
│   Layer 1 (Middle): CONTENT AREA (Text OR Video - mutual exclusion) │
│                     - Text: paragraphs, bullets, numbered, formulas │
│                     - Video: Manim animation OR WAN video           │
│                     - Fills FULLSCREEN when visual_layer="show"     │
│                     - Content types: paragraph|bullet|ordered|formula│
│                                                                      │
│   Layer 0 (Bottom): BACKGROUND BLACK                                │
│                     - Always black, no images                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Dev Mode Features (Planned)
- Resize and move Content Box
- Resize and move Video Box  
- Resize and move Avatar position
- All adjustments saved to presentation.json for replay

---

## Content Display Modes (ISS-160)

The player MUST render content based on `content_type` from visual_content:

### Paragraph Mode (content_type: "paragraph")
```
┌─────────────────────────────────────────┐
│  Trigonometry is the study of           │
│  relationships between angles and       │
│  sides of triangles. The ratio          │
│  $\sin\theta$ represents the opposite   │
│  side divided by the hypotenuse.        │
└─────────────────────────────────────────┘
```
- Displays as flowing prose text (NOT bullets)
- Inline LaTeX renders within paragraph via MathJax
- Uses `verbatim_text` field directly
- Line breaks respected from source

### Bullet List Mode (content_type: "bullet_list")
```
┌─────────────────────────────────────────┐
│  • Sine (sin) - opposite/hypotenuse     │
│  • Cosine (cos) - adjacent/hypotenuse   │
│  • Tangent (tan) - opposite/adjacent    │
└─────────────────────────────────────────┘
```
- Displays with bullet markers (•)
- Uses `bullet_points[]` array
- Nested levels supported via `level` field

### Ordered List Mode (content_type: "ordered_list")
```
┌─────────────────────────────────────────┐
│  1. Identify the angle θ                │
│  2. Label opposite, adjacent, hypotenuse│
│  3. Apply the correct ratio formula     │
│  4. Calculate the final value           │
└─────────────────────────────────────────┘
```
- Displays with numbered markers (1., 2., 3.)
- Uses `ordered_list[]` array
- Maintains source order exactly

### Formula Mode (content_type: "formula")
```
┌─────────────────────────────────────────┐
│                                         │
│         sin θ = opposite                │
│                 ─────────               │
│                 hypotenuse              │
│                                         │
└─────────────────────────────────────────┘
```
- Centered block LaTeX rendering
- Uses `formula` or `formulas[]` field
- MathJax renders $$...$$ notation

### Fullscreen Video Mode (visual_layer: "show")
```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    ┌─────────────────────────┐                    │
│                    │                         │                    │
│     VIDEO FILLS    │     MANIM/WAN VIDEO     │     ENTIRE        │
│     CONTENT AREA   │     PLAYING             │     SCREEN        │
│                    │                         │                    │
│                    └─────────────────────────┘                    │
│                                                   ┌───────────┐   │
│                                                   │  AVATAR   │   │
│                                                   │  52%      │   │
│                                                   └───────────┘   │
└───────────────────────────────────────────────────────────────────┘
```
- Video fills content area (text hidden)
- Avatar remains visible at 52% right
- Triggered when `visual_layer: "show"`

---

## Flip Timing (ISS-160)

### LLM-Controlled Flip

The `flip_timing_sec` field in display_directives controls when to transition:

```
Segment Duration: 10 seconds
flip_timing_sec: 4.0

Timeline:
0s ──────── 4s ──────── 10s
|── TEXT ──|── VIDEO ──|

Narration: "Let me show you the formula..."
           ↑ At 4s: text fades, video shows formula
```

### Player Logic

```javascript
// ONLY flip if LLM explicitly specifies timing
const flipAt = segment.display_directives?.flip_timing_sec;
if (flipAt !== null && flipAt !== undefined) {
  if (elapsedInSegment >= flipAt) {
    showVisualLayer();
    hideTextLayer();
  }
}
// If flipAt is null/undefined → NO flip, show text entire segment
```

### Key Rules

1. `flip_timing_sec: null` → NO flip occurs (text stays)
2. `flip_timing_sec: 0` → Immediate video (no text shown)
3. `flip_timing_sec: 4.5` → Text for 4.5s, then video
4. Player has NO default - LLM must specify or nothing happens

---

## Section Type Layouts (ASCII)

### Section 1: INTRO

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INTRO LAYOUT                               │
│                        Avatar: CENTER, 52%                           │
│                    (990x557px at 1920x1080)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                  TEXT AREA (914x502px)                       │  │
│   │                  Position: L:65px T:70px                     │  │
│   │                                                              │  │
│   │   "Welcome to Definite Integrals!"                           │  │
│   │   - Today we explore integration                             │  │
│   │   - You'll learn the fundamental theorem                     │  │
│   │                                                              │  │
│   └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│                    ┌─────────────────────────┐                       │
│                    │                         │                       │
│                    │     AVATAR (CENTER)     │                       │
│                    │     Size: 990x557px     │                       │
│                    │     Width: 52%          │                       │
│                    │     Pos: R:46px B:1px   │                       │
│                    │                         │                       │
│                    └─────────────────────────┘                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "show", visual_layer: "hide", avatar_layer: "show" }
avatar_layout: { position: "center", width_percent: 52, size: "990x557" }
renderer: none
```

---

### Section 2: SUMMARY

```
┌─────────────────────────────────────────────────────────────────────┐
│                          SUMMARY LAYOUT                              │
│                        Avatar: RIGHT, 52%                            │
│                    (1008x567px at 1920x1080)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────┐   ┌─────────────────────────────┐   │
│   │   TEXT AREA (Left 45%)    │   │      AVATAR (RIGHT)         │   │
│   │   Size: 850x777px         │   │                             │   │
│   │   WHAT YOU'LL LEARN       │   │     Size: 1008x567px        │   │
│   │                           │   │     Width: 52%              │   │
│   │   - Define integrals      │   │     Pos: R:-245px B:1px     │   │
│   │   - Properties overview   │   │                             │   │
│   │   - Fundamental theorem   │   │                             │   │
│   │   - Worked examples       │   │                             │   │
│   │                           │   │                             │   │
│   └───────────────────────────┘   └─────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "show", visual_layer: "hide", avatar_layer: "show" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: none
```

---

### Section 3-N: CONTENT (Text Mode)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONTENT LAYOUT (Text Mode)                       │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────────────────────┐   ┌──────────────────────────┐   │
│   │   TEXT AREA (Left 60%)       │   │     AVATAR (RIGHT)       │   │
│   │                              │   │                          │   │
│   │   CONTENT FROM SOURCE        │   │      Width: 52%          │   │
│   │   (P7: Input file only!)     │   │      Small-Medium        │   │
│   │                              │   │      Explaining          │   │
│   │   - Key concept 1            │   │                          │   │
│   │   - Key concept 2            │   │                          │   │
│   │   - Formula: ∫f(x)dx         │   │                          │   │
│   │                              │   │                          │   │
│   └──────────────────────────────┘   └──────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "show", visual_layer: "hide", avatar_layer: "show" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: manim (but video not playing yet)
```

---

### Section 3-N: CONTENT (Video Mode - Manim/WAN)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONTENT LAYOUT (Video Mode)                      │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │                                                               │ │
│   │                    VIDEO AREA (Fullscreen)                    │ │
│   │                    Manim Animation / WAN                      │ │
│   │                                                               │ │
│   │     [Animated graphs, equations, visual explanations]         │ │
│   │                                                               │ │
│   │                                                               │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                                           ┌─────────────────────┐   │
│                                           │   AVATAR (RIGHT)    │   │
│                                           │    Width: 52%       │   │
│                                           │    gesture_only*    │   │
│                                           └─────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "hide", visual_layer: "show", avatar_layer: "gesture_only" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: manim or video

* gesture_only = Avatar IS VISIBLE, but the avatar VIDEO was generated 
  with gesturing only (no lip-sync). This is generation metadata, NOT display hiding.
```

---

### Section: EXAMPLE

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXAMPLE LAYOUT                               │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────────────────────┐   ┌──────────────────────────┐   │
│   │   WORKED EXAMPLE (Left 60%)  │   │     AVATAR (RIGHT)       │   │
│   │                              │   │                          │   │
│   │   Problem:                   │   │      Width: 52%          │   │
│   │   Evaluate ∫₀² (3x²+2x) dx   │   │      Explaining          │   │
│   │                              │   │                          │   │
│   │   Step 1: Antiderivative     │   │                          │   │
│   │   Step 2: Apply bounds       │   │                          │   │
│   │   Step 3: Calculate          │   │                          │   │
│   │                              │   │                          │   │
│   │   Answer: 16                 │   │                          │   │
│   └──────────────────────────────┘   └──────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "show", visual_layer: "show", avatar_layer: "show" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: manim
```

---

### Section: QUIZ (Conditional - Flashcard Style)

**Conditional**: Quiz section only generated if source PDF contains quiz questions.

**Source**: Q&A pairs extracted directly from PDF by SmartChunker (not LLM-generated).

**Flow**: SmartChunker → SectionPlanner (creates quiz section if quiz_questions exist) → NarrationWriter (formats Q&A with pauses) → TTS

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUIZ LAYOUT (Flashcard Style)                     │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────────────────────┐  ┌───────────────┐  │
│   │                                           │  │               │  │
│   │   ┌───────────────────────────────────┐   │  │    AVATAR     │  │
│   │   │        FLASHCARD (Front)          │   │  │    (RIGHT)    │  │
│   │   │   ─────────────────────────────   │   │  │               │  │
│   │   │   Question 1:                     │   │  │   Width: 52%  │  │
│   │   │   What is the derivative of x²?   │   │  │               │  │
│   │   │                                   │   │  │   Narrating:  │  │
│   │   │   [3 second pause for thinking]   │   │  │   "Let's test │  │
│   │   │                                   │   │  │    what you   │  │
│   │   └───────────────────────────────────┘   │  │    learned"   │  │
│   │                                           │  │               │  │
│   │   After pause, card flips to show answer: │  │               │  │
│   │   ┌───────────────────────────────────┐   │  │               │  │
│   │   │        FLASHCARD (Back)           │   │  │               │  │
│   │   │   ─────────────────────────────   │   │  │               │  │
│   │   │   Answer: 2x                      │   │  │               │  │
│   │   │                                   │   │  │               │  │
│   │   └───────────────────────────────────┘   │  │               │  │
│   │                                           │  │               │  │
│   └───────────────────────────────────────────┘  └───────────────┘  │
│                                                                      │
│   Cycles through all Q&A pairs (variable count from PDF)            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "show", visual_layer: "hide", avatar_layer: "show" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: none

Quiz vs Memory:
- Quiz: CONDITIONAL (only if PDF has quiz), variable count, source from PDF
- Memory: MANDATORY (always generated), fixed 5 flashcards, LLM-summarized
```

---

### Section: MEMORY (Flashcards)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MEMORY LAYOUT                                │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────────────────────┐  ┌───────────────┐  │
│   │                                           │  │    AVATAR     │  │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │    (RIGHT)    │  │
│   │   │ CARD 1  │ │ CARD 2  │ │ CARD 3  │     │  │               │  │
│   │   │ Q: What │ │ Q: For- │ │ Q: When │     │  │  Width: 52%   │  │
│   │   │ is...?  │ │ mula?   │ │ to use? │     │  │               │  │
│   │   │         │ │         │ │         │     │  │               │  │
│   │   │ A: ...  │ │ A: ∫    │ │ A: ...  │     │  │               │  │
│   │   └─────────┘ └─────────┘ └─────────┘     │  │               │  │
│   │                                           │  │               │  │
│   │   ┌─────────┐ ┌─────────┐                 │  │               │  │
│   │   │ CARD 4  │ │ CARD 5  │                 │  │               │  │
│   │   └─────────┘ └─────────┘                 │  │               │  │
│   │                                           │  │               │  │
│   └───────────────────────────────────────────┘  └───────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "hide", visual_layer: "show", avatar_layer: "show" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: none
```

---

### Section: RECAP

```
┌─────────────────────────────────────────────────────────────────────┐
│                          RECAP LAYOUT                                │
│                        Avatar: RIGHT, 52%                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │                                                               │ │
│   │                    WAN VIDEO (Fullscreen)                     │ │
│   │                                                               │ │
│   │     [AI-generated cinematic video summarizing concepts]       │ │
│   │                                                               │ │
│   │                                                               │ │
│   │                                                               │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                                           ┌─────────────────────┐   │
│                                           │   AVATAR (RIGHT)    │   │
│                                           │    Width: 52%       │   │
│                                           │    gesture_only     │   │
│                                           └─────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

display_directives: { text_layer: "hide", visual_layer: "show", avatar_layer: "gesture_only" }
avatar_layout: { position: "right", width_percent: 52 }
renderer: video (WAN)
```

---

## LLM Agent Reference

### Pipeline Overview

```
PDF/MD Input
    │
    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         V1.5 AGENT PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐                                                        │
│  │ CHUNKER  │ ──────────────────────────────────────────────────┐    │
│  └──────────┘                                                   │    │
│       │ topics[]                                                │    │
│       ▼                                                         │    │
│  ┌────────────────┐                                             │    │
│  │ SECTION PLANNER│ ──────────────────────────────────────┐     │    │
│  └────────────────┘                                       │     │    │
│       │ sections[]                                        │     │    │
│       ▼                                                   │     │    │
│  ┌──────────────────┐                                     │     │    │
│  │ NARRATION WRITER │ (per section)                       │     │    │
│  └──────────────────┘                                     │     │    │
│       │ narration + segments[]                            │     │    │
│       ▼                                                   │     │    │
│  ┌───────────────────┐                                    │     │    │
│  │ VISUAL SPEC ARTIST│ (per section)                      │     │    │
│  └───────────────────┘                                    │     │    │
│       │ visual_beats[] + display_directives[]             │     │    │
│       ▼                                                   │     │    │
│  ┌─────────────────┐                                      │     │    │
│  │ RENDERER SPEC   │ (manim/video sections only)          │     │    │
│  └─────────────────┘                                      │     │    │
│       │ manim_scene_spec / video_prompts                  │     │    │
│       │                                                   │     │    │
│       │  ┌──────────────┐  ┌──────────────┐               │     │    │
│       └──│ MEMORY AGENT │  │ RECAP AGENT  │◄──────────────┴─────┘    │
│          └──────────────┘  └──────────────┘                          │
│                │ flashcards[]    │ video_prompts[]                   │
│                └────────┬────────┘                                   │
│                         ▼                                            │
│                  ┌────────────┐                                      │
│                  │ MERGE STEP │                                      │
│                  └────────────┘                                      │
│                         │                                            │
│                         ▼                                            │
│                  ┌────────────┐                                      │
│                  │    TTS     │ (Edge TTS / Narakeet)                │
│                  └────────────┘                                      │
│                         │ actual audio durations                     │
│                         ▼                                            │
│                  ┌────────────────────┐                              │
│                  │ presentation.json  │                              │
│                  └────────────────────┘                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Agent 1: CHUNKER

| Property | Value |
|----------|-------|
| **Purpose** | Extract logical topics from PDF/MD content |
| **Prompt Files** | `core/prompts/smart_chunker_system_v1.4.txt`, `core/prompts/smart_chunker_user_v1.4.txt` |
| **Python File** | (uses director pipeline in v1.4) |
| **Input** | Raw markdown content with [BLOCK N] markers |
| **Output Fields** | `source_topic`, `topics[]` (topic_id, title, concept_type, source_blocks, key_terms, has_formula, suggested_renderer) |
| **Avatar Fields** | None (pre-section planning) |
| **Changes Needed** | None |

---

### Agent 2: SECTION PLANNER

| Property | Value |
|----------|-------|
| **Purpose** | Create section structure from topics |
| **Prompt Files** | `core/prompts/section_planner_system_v1.5.txt`, `core/prompts/section_planner_user_v1.5.txt` |
| **Python File** | `core/agents/section_planner.py` |
| **Input** | Chunker output (topics[]) |
| **Output Fields** | `sections[]` (section_id, section_type, title, source_topics, learning_goals, suggested_renderer, renderer_reasoning, avatar_visibility, avatar_position, estimated_duration_seconds) |

#### Avatar Fields - CHANGES NEEDED

| Current Field | Current Values | Required Change |
|---------------|----------------|-----------------|
| `avatar_visibility` | required, optional, hidden | Remove "hidden" - avatar always visible |
| `avatar_position` | left, right, center, hidden | Remove "hidden" - always visible |
| **NEW** `avatar_width_percent` | N/A | Add: 60 (intro), 45 (summary), 35 (others) |

#### Output Schema Update

```json
{
  "sections": [{
    "section_id": "section_1",
    "section_type": "intro",
    "avatar_visibility": "required",
    "avatar_position": "center",
    "avatar_width_percent": 60
  }]
}
```

---

### Agent 3: NARRATION WRITER

| Property | Value |
|----------|-------|
| **Purpose** | Write TTS narration scripts per section |
| **Prompt Files** | `core/prompts/narration_writer_system_v1.5.txt`, `core/prompts/narration_writer_user_v1.5.txt` |
| **Python File** | `core/agents/narration_writer.py` |
| **Input** | Section plan + source content |
| **Output Fields** | `section_id`, `narration.full_text`, `narration.segments[]` (segment_id, text, duration_seconds, gesture_hint) |
| **Avatar Fields** | `gesture_hint` (pointing, explaining, emphasizing, welcoming, thinking) - for avatar generation |
| **Changes Needed** | None (gesture_hint is already avatar generation metadata) |

---

### Agent 4: VISUAL SPEC ARTIST

| Property | Value |
|----------|-------|
| **Purpose** | Design visual elements synchronized with narration |
| **Prompt Files** | `core/prompts/visual_spec_artist_system_v1.5.txt`, `core/prompts/visual_spec_artist_user_v1.5.txt` |
| **Python File** | `core/agents/visual_spec_artist.py` |
| **Input** | Section plan + narration segments |
| **Output Fields** | `section_id`, `visual_beats[]`, `segment_enrichments[]` (visual_content, display_directives) |

#### Avatar Fields - CHANGES NEEDED

| Current Field | Current Values | Required Change |
|---------------|----------------|-----------------|
| `display_directives.avatar_layer` | show, hide, gesture_only | Remove "hide" option |

#### Clarification

- `avatar_layer: "show"` = Avatar visible, lip-sync video generated
- `avatar_layer: "gesture_only"` = Avatar visible, gesture-only video generated (no lip-sync during heavy visuals)
- ~~`avatar_layer: "hide"`~~ = REMOVE - avatar never hidden

---

### Agent 5: RENDERER SPEC

| Property | Value |
|----------|-------|
| **Purpose** | Create Manim/Video rendering specifications |
| **Prompt Files** | `core/prompts/manim_spec_system_v1.5.txt`, `core/prompts/video_prompt_system_v1.5.txt` |
| **Python File** | `core/agents/renderer_spec_agent.py` |
| **Input** | Section plan + visual beats |
| **Output Fields** | `manim_scene_spec` OR `video_prompts[]` |
| **Avatar Fields** | None (rendering only) |
| **Changes Needed** | None |

---

### Agent 6: MEMORY AGENT

| Property | Value |
|----------|-------|
| **Purpose** | Generate 5 flashcards for review |
| **Prompt Files** | `core/prompts/memory_flashcard_system_v1.5.txt`, `core/prompts/memory_flashcard_user_v1.5.txt` |
| **Python File** | `core/agents/memory_agent.py` |
| **Input** | All section content |
| **Output Fields** | `section_id`, `section_type`, `title`, `flashcards[]` (flashcard_id, front, back, category) |

#### Avatar Fields - CHANGES NEEDED

| Current Field | Required Addition |
|---------------|-------------------|
| None | Add `avatar_layout: { position: "right", width_percent: 52 }` |

---

### Agent 7: RECAP AGENT

| Property | Value |
|----------|-------|
| **Purpose** | Generate 5 video prompts for WAN recap |
| **Prompt Files** | `core/prompts/recap_scene_system_v1.5.txt`, `core/prompts/recap_scene_user_v1.5.txt` |
| **Python File** | `core/agents/recap_agent.py` |
| **Input** | All section content |
| **Output Fields** | `section_id`, `section_type`, `title`, `video_prompts[]` (prompt_id, prompt, duration_seconds, style) |

#### Avatar Fields - CHANGES NEEDED

| Current Field | Required Addition |
|---------------|-------------------|
| None | Add `avatar_layout: { position: "right", width_percent: 52 }` |

---

## Implementation Checklist

### Prompt File Changes

| File | Change | Status |
|------|--------|--------|
| `core/prompts/section_planner_system_v1.5.txt` | Add `avatar_width_percent` field (52% for all) | COMPLETE |
| `core/prompts/section_planner_system_v1.5.txt` | Remove "hidden" from avatar_visibility and avatar_position | PENDING |
| `core/prompts/visual_spec_artist_system_v1.5.txt` | Remove "hide" from avatar_layer options | PENDING |
| `core/prompts/memory_flashcard_system_v1.5.txt` | Add `avatar_layout` output field | PENDING |
| `core/prompts/recap_scene_system_v1.5.txt` | Add `avatar_layout` output field | PENDING |

### Python Agent Changes

| File | Function | Change | Status |
|------|----------|--------|--------|
| `core/agents/section_planner.py` | `validate_output()` | Validate avatar_width_percent (52% for all types) | COMPLETE |
| `core/agents/visual_spec_artist.py` | `validate_output()` | Remove "hide" validation for avatar_layer | PENDING |
| `core/agents/memory_agent.py` | `run()` | Output avatar_layout in response | PENDING |
| `core/agents/recap_agent.py` | `run()` | Output avatar_layout in response | PENDING |

### Player Changes

| File | Function/Section | Change | Status |
|------|------------------|--------|--------|
| `player/player.js` | `LayerController.updateLayers()` | Remove logic that hides avatar on avatar_layer="hide" | COMPLETE (ISS-136) |
| `player/player.js` | `LayerController.updateLayers()` | Avatar ALWAYS visible, ignore "hide" value | COMPLETE (ISS-136) |
| `player/player.js` | `getDefaultAvatarWidth()` | Return 52% for ALL section types | COMPLETE (ISS-141) |
| `player/index.html` | CSS | Width classes not needed - uses inline width_percent | COMPLETE |

### Merge Step Changes

| File | Function | Change | Status |
|------|----------|--------|--------|
| `core/merge_step_v15.py` | `merge_section()` | Include avatar_layout from agents into section output | COMPLETE (ISS-131) |

---

## Narration Sync Architecture

### Timing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      NARRATION SYNC FLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. NARRATION WRITER                                                 │
│     │                                                                │
│     │  Outputs: segments[] with estimated duration                   │
│     │  Formula: duration_seconds = word_count / 130 * 60             │
│     │                                                                │
│     ▼                                                                │
│  2. VISUAL SPEC ARTIST                                               │
│     │                                                                │
│     │  References: segment_id in visual_beats[]                      │
│     │  Outputs: display_directives per segment                       │
│     │                                                                │
│     ▼                                                                │
│  3. MERGE STEP                                                       │
│     │                                                                │
│     │  Combines: segment + visual_content + display_directives       │
│     │  Creates: unified section structure                            │
│     │                                                                │
│     ▼                                                                │
│  4. TTS PASS (Edge TTS)                                              │
│     │                                                                │
│     │  Generates: audio file per segment                             │
│     │  Measures: actual audio duration via mutagen                   │
│     │  UPDATES: segment.duration_seconds = actual audio length       │
│     │  Consolidates: segment audio → section_X.mp3 (ISS-115)         │
│     │                                                                │
│     ▼                                                                │
│  5. PLAYER                                                           │
│     │                                                                │
│     │  Reads: segment.duration_seconds for playback timing           │
│     │  Reads: display_directives to show/hide layers                 │
│     │  Syncs: audio playback with visual transitions                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Invariants

1. `sum(segment.duration_seconds) = section total duration`
2. `visual_beat[i].segment_id` maps to `segment[i]`
3. `display_directives[i]` corresponds to `segment[i]`
4. TTS audio duration is the AUTHORITATIVE timing source
5. All visual transitions sync to audio timeline

### Audio File Structure

```
player/jobs/{job_id}/
├── section_1.mp3          # Consolidated audio for section 1
├── section_2.mp3          # Consolidated audio for section 2
├── ...
├── videos/
│   ├── topic_1.mp4        # Manim/WAN rendered video
│   ├── topic_2.mp4
│   └── ...
└── presentation.json      # Master playback file
```

---

## Requirement Tracking

### Display Requirements

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-001 | Intro section: Avatar CENTER, 52% width | COMPLETE (ISS-141) | section_planner prompt, player.js |
| REQ-002 | Summary section: Avatar RIGHT, 52% width | COMPLETE (ISS-141) | section_planner prompt, player.js |
| REQ-003 | Content/Example/Quiz/Memory/Recap: Avatar RIGHT, 52% width | COMPLETE (ISS-141) | section_planner prompt, player.js |
| REQ-004 | Avatar ALWAYS VISIBLE (remove "hide" option) | COMPLETE (ISS-136) | section_planner prompt, visual_spec_artist prompt, player.js |
| REQ-005 | gesture_only = avatar generation metadata, not display hiding | COMPLETE | Documentation only (already correct) |
| REQ-006 | Video fills screen when playing (Manim/WAN) | COMPLETE | player.js, player CSS |

### Layer Requirements

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-010 | Layer 0: Background always black | VERIFIED | player/index.html CSS |
| REQ-011 | Layer 1: Content area (Text OR Video, mutual exclusion) | VERIFIED | player.js |
| REQ-012 | Layer 2: Avatar always rendered on top | COMPLETE (ISS-136) | player.js |

### Prompt Changes

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-020 | SectionPlanner: Add avatar_width_percent field | COMPLETE | core/prompts/section_planner_system_v1.5.txt |
| REQ-021 | SectionPlanner: Remove "hidden" from avatar options | COMPLETE | core/prompts/section_planner_system_v1.5.txt |
| REQ-022 | VisualSpecArtist: Remove "hide" from avatar_layer | COMPLETE | core/prompts/visual_spec_artist_system_v1.5.txt |
| REQ-023 | MemoryAgent: Add avatar_layout output | COMPLETE | core/prompts/memory_flashcard_system_v1.5.txt |
| REQ-024 | RecapAgent: Add avatar_layout output | COMPLETE | core/prompts/recap_scene_system_v1.5.txt |

### Player Changes

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-030 | Player: Avatar never hidden, always Layer 2 | COMPLETE | player/player.js |
| REQ-031 | Player: Apply avatar_width_percent from section | COMPLETE | player/player.js |
| REQ-032 | Player: Dev mode resize/move content box | FUTURE | player/player.js |
| REQ-033 | Player: Dev mode resize/move video box | FUTURE | player/player.js |
| REQ-034 | Player: Dev mode resize/move avatar | FUTURE | player/player.js |

### Narration Sync

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-040 | TTS duration updates segment.duration_seconds | VERIFIED | core/tts_generator.py |
| REQ-041 | Audio consolidated into section_X.mp3 | VERIFIED (ISS-115) | core/tts_generator.py |
| REQ-042 | Player syncs to segment.duration_seconds | VERIFIED | player/player.js |

### Test Coverage

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-050 | Test document with ALL section types | COMPLETE | test_docs/comprehensive_test.md |
| REQ-051 | Test generates: intro, summary, content, example, quiz, memory, recap | PENDING | Test execution |
| REQ-052 | Manim renders correctly for content sections | PENDING | Test execution |

### Manim Code Generation

| REQ-ID | Description | Status | Files Affected |
|--------|-------------|--------|----------------|
| REQ-060 | ManimCodeGenerator generates Python code directly (not JSON spec) | COMPLETE | core/agents/manim_code_generator.py |
| REQ-061 | Use Claude Sonnet 4.5 via OpenRouter for Manim code generation | COMPLETE | core/agents/manim_code_generator.py |
| REQ-062 | Use new prompts: manim_system_prompt.txt + manim_user_prompt_template.txt | COMPLETE | core/prompts/ |
| REQ-063 | Manim code validation: syntax check, no Dot() placeholders | COMPLETE | core/agents/manim_code_generator.py |
| REQ-064 | Manim code validation: timing matches segment durations | COMPLETE | core/agents/manim_code_generator.py |
| REQ-065 | Auto-retry on validation failure with clearer prompt | COMPLETE | core/agents/manim_code_generator.py |
| REQ-066 | Wire TTS actual duration to Manim Code Generator input | COMPLETE | core/pipeline_v15.py (Pass 5 post-TTS) |
| REQ-067 | Connect VisualSpecArtist visual descriptions to Manim input | COMPLETE | core/pipeline_v15.py (build_manim_section_data) |
| REQ-068 | Local Manim renderer accepts manim_code field directly | VERIFIED | Existing renderer works |

---

## Manim Code Generation

### Overview

The Manim Code Generator produces Python code for Manim Community animations, synchronized to narration timing from TTS.

### Key Change from Previous Approach

| Aspect | Previous (V1.5) | New Approach |
|--------|-----------------|--------------|
| **LLM Output** | JSON spec (objects, animations) | Raw Python code |
| **Prompt** | manim_spec_system_v1.5.txt | manim_system_prompt.txt + manim_user_prompt_template.txt |
| **LLM Model** | Gemini 2.5 / Claude Sonnet | **Claude Sonnet 4.5** via OpenRouter |
| **Renderer Input** | Interprets JSON → generates code | Executes Python code directly |

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MANIM CODE GENERATION FLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. NARRATION WRITER                                                 │
│     │  Output: segments[] with estimated duration                    │
│     ▼                                                                │
│  2. TTS PASS (Edge TTS)                                              │
│     │  Output: ACTUAL duration per segment (source of truth)         │
│     ▼                                                                │
│  3. VISUAL SPEC ARTIST                                               │
│     │  Output: visual_beats[].description per segment                │
│     ▼                                                                │
│  4. MANIM CODE GENERATOR (New)                                       │
│     │                                                                │
│     │  Input:                                                        │
│     │  ┌─────────────────────────────────────────────────────────┐  │
│     │  │ {                                                       │  │
│     │  │   "section_title": "Definite Integral",                 │  │
│     │  │   "narration_segments": [                               │  │
│     │  │     {                                                   │  │
│     │  │       "start": 0,                                       │  │
│     │  │       "duration": 5.2,  // FROM TTS                     │  │
│     │  │       "text": "The definite integral...",               │  │
│     │  │       "visual": "Show axes, plot curve"  // FROM VSA    │  │
│     │  │     }                                                   │  │
│     │  │   ],                                                    │  │
│     │  │   "total_duration": 20.0,                               │  │
│     │  │   "formulas": ["∫ₐᵇ f(x)dx"],                           │  │
│     │  │   "key_terms": ["integral", "limits"]                   │  │
│     │  │ }                                                       │  │
│     │  └─────────────────────────────────────────────────────────┘  │
│     │                                                                │
│     │  LLM: Claude Sonnet 4.5 (anthropic/claude-sonnet-4.5)          │
│     │  System Prompt: core/prompts/manim_system_prompt.txt           │
│     │  User Prompt: core/prompts/manim_user_prompt_template.txt      │
│     │                                                                │
│     │  Output: Python code for construct(self) method body           │
│     ▼                                                                │
│  5. VALIDATION                                                       │
│     │  - Syntax check (compile test)                                 │
│     │  - No Dot() placeholders                                       │
│     │  - Timing: sum(run_time + wait) = segment duration             │
│     │  - On failure: auto-retry with clearer prompt                  │
│     ▼                                                                │
│  6. LOCAL MANIM RENDERER                                             │
│     │                                                                │
│     │  JSON Input:                                                   │
│     │  {                                                             │
│     │    "sections": [{                                              │
│     │      "section_id": "3",                                        │
│     │      "prompts": [{                                             │
│     │        "prompt": "...",                                        │
│     │        "manim_code": "<Python code from LLM>"                  │
│     │      }]                                                        │
│     │    }],                                                         │
│     │    "quality_preset": "preview|production",                     │
│     │    "use_cache": true                                           │
│     │  }                                                             │
│     │                                                                │
│     │  Output: MP4 video file                                        │
│     ▼                                                                │
│  7. videos/topic_X.mp4 → Player                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Prompt Files

| File | Location | Purpose |
|------|----------|---------|
| **System Prompt** | `core/prompts/manim_system_prompt.txt` | Rules for Manim code generation |
| **User Template** | `core/prompts/manim_user_prompt_template.txt` | Template with timing placeholders |

### System Prompt Key Rules

1. Use ONLY Manim Community (manim) - NOT ManimGL
2. Generate code for `construct(self)` method body ONLY - no imports, no class
3. NEVER use `Dot()` as placeholder - use actual objects
4. Match narration segment timing EXACTLY
5. Each segment: `run_time + self.wait() = segment duration`

### User Prompt Template Variables

| Variable | Source |
|----------|--------|
| `{section_title}` | SectionPlanner output |
| `{narration_segments}` | NarrationWriter + TTS + VisualSpecArtist |
| `{visual_description}` | VisualSpecArtist visual_beats |
| `{formulas}` | VisualSpecArtist segment_enrichments |
| `{key_terms}` | VisualSpecArtist labels |
| `{total_duration}` | Sum of TTS segment durations |
| `{special_requirements}` | Optional styling notes |

### Validation Rules

| Check | Pass Criteria | On Failure |
|-------|---------------|------------|
| Syntax | `compile(code, '<string>', 'exec')` succeeds | Retry with error message |
| No Placeholders | No `Dot()` in code | Retry with "use actual objects" |
| Timing Match | `sum(run_time + wait)` ≈ segment duration (±0.5s) | Retry with timing breakdown |
| Variable Names | No overwrites like `axes = axes.plot()` | Retry with warning |

### Auto-Retry Logic

```python
MAX_RETRIES = 3

for attempt in range(MAX_RETRIES):
    code = generate_manim_code(section_data)
    errors = validate_manim_code(code, section_data)
    
    if not errors:
        return code
    
    # Add errors to prompt for clearer regeneration
    section_data["previous_errors"] = errors
    section_data["special_requirements"] += f"\n\nFix these issues: {errors}"

raise ManimCodeGenerationError(f"Failed after {MAX_RETRIES} attempts")
```

---

## Test Plan

### Test Levels

| Level | What We Test | Method | Status |
|-------|--------------|--------|--------|
| **TEST-001** | LLM Agents | Python unit tests for each agent | PENDING |
| **TEST-002** | Display | Screenshot + visual inspection | PENDING |
| **TEST-003** | End-to-End | curl API call to /api/v15/generate | PENDING |

### TEST-001: LLM Agent Tests

Test each agent in isolation with `test_docs/comprehensive_test.md`:

| Agent | Test | Expected Output | Status |
|-------|------|-----------------|--------|
| Chunker | Parse test doc | 5+ topics extracted | PENDING |
| SectionPlanner | Plan sections | intro, summary, 5 content, example, memory, recap | PENDING |
| NarrationWriter | Write narration | Valid segments with timing | PENDING |
| VisualSpecArtist | Create visuals | visual_beats + display_directives | PENDING |
| ManimCodeGenerator | Generate code | Valid Python, correct timing | PENDING |
| MemoryAgent | Create flashcards | 5 flashcards | PENDING |
| RecapAgent | Create video prompts | 5 prompts, <1000 chars each | PENDING |

**Test Script Location**: `tests/test_llm_agents.py` (to be created)

### TEST-002: Display Tests

Verify avatar sizing and layer behavior across all section types:

| Section | Avatar Position | Avatar Width | Check |
|---------|-----------------|--------------|-------|
| Intro | Center | 52% | Visual |
| Summary | Right | 52% | Visual |
| Content | Right | 52% | Visual |
| Example | Right | 52% | Visual |
| Quiz | Right | 52% | Visual |
| Memory | Right | 52% | Visual |
| Recap | Right | 52% | Visual |

**Test Method**: Run pipeline, take screenshots, verify avatar placement

### TEST-003: End-to-End Test

Full pipeline test via API:

```bash
# Start the server
python api/app.py

# Run E2E test
curl -X POST http://localhost:5000/api/v15/generate \
  -H "Content-Type: application/json" \
  -d '{
    "input_file": "test_docs/comprehensive_test.md",
    "pipeline_version": "v15"
  }'

# Check job status
curl http://localhost:5000/api/v15/status/{job_id}

# Verify output
# - All sections generated (intro, summary, content, example, quiz, memory, recap)
# - All Manim videos rendered
# - TTS audio generated
# - presentation.json valid
# - Player can load and play
```

**Test Script Location**: `tests/test_e2e.sh` (to be created)

### Test Execution Order

1. **Unit Tests First** - Verify each agent works
2. **Integration Tests** - Verify agents work together
3. **Display Tests** - Verify player renders correctly
4. **E2E Tests** - Verify full pipeline end-to-end

---

## Test Input Document

### Required Test Document Structure

To ensure all section types are generated and tested, the input document must contain:

1. **Clear introduction hook** → triggers INTRO section
2. **Learning objectives list** → triggers SUMMARY section  
3. **3-5 conceptual topics** → triggers CONTENT sections
4. **At least one worked example** → triggers EXAMPLE section
5. **Quiz-style questions** (optional) → triggers QUIZ section
6. **Key terms and formulas** → triggers MEMORY flashcards
7. **Summary concepts** → triggers RECAP video generation

### Sample Test Document Location

**File**: `test_docs/comprehensive_test.md` (to be created)

### Sample Structure

```markdown
# [Topic Name]

## Introduction
Brief hook about why this topic matters...

## Learning Objectives
By the end of this lesson, you will be able to:
- Objective 1
- Objective 2
- Objective 3

## Core Concepts

### Concept 1: [Name]
Detailed explanation with formula: [LaTeX]
Key terms: term1, term2

### Concept 2: [Name]
Detailed explanation...

### Concept 3: [Name]
Detailed explanation with formula...

## Worked Example
**Problem**: [Problem statement]
**Solution**:
Step 1: ...
Step 2: ...
Step 3: ...
**Answer**: [Result]

## Practice Quiz
1. Question 1?
   a) Option A
   b) Option B
   c) Option C
   
2. Question 2?
   ...

## Summary
Key takeaways:
- Point 1
- Point 2
- Point 3
```

---

## Open Items

| ID | Description | Owner | Status |
|----|-------------|-------|--------|
| OPEN-001 | Manim code update | USER TO PROVIDE | PENDING |
| OPEN-002 | Dev mode implementation (resize/move boxes) | FUTURE | NOT STARTED |
| OPEN-003 | Quiz section renderer (if needed) | TBD | NOT STARTED |

---

## File References

| Component | File Location |
|-----------|---------------|
| **This Document** | `docs/display_requirements.md` |
| **V1.5 Spec** | `docs/v1.5_requirements.json` |
| **Player Logic** | `player/player.js` |
| **Player UI** | `player/index.html` |
| **Presentation Data** | `player/jobs/{job_id}/presentation.json` |
| **SectionPlanner Prompt** | `core/prompts/section_planner_system_v1.5.txt` |
| **VisualSpecArtist Prompt** | `core/prompts/visual_spec_artist_system_v1.5.txt` |
| **MemoryAgent Prompt** | `core/prompts/memory_flashcard_system_v1.5.txt` |
| **RecapAgent Prompt** | `core/prompts/recap_scene_system_v1.5.txt` |
| **Manim System Prompt** | `core/prompts/manim_system_prompt.txt` |
| **Manim User Template** | `core/prompts/manim_user_prompt_template.txt` |
| **Test Document** | `test_docs/comprehensive_test.md` |
| **LLM Agent Tests** | `tests/test_llm_agents.py` (to be created) |
| **E2E Test Script** | `tests/test_e2e.sh` (to be created) |

---

*Last Updated: 2025-12-24*
*Document Version: 2.0*
