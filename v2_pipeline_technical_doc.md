# V2 Pipeline Technical Documentation

## AI Animated Education - V1.5-V2 Unified Pipeline

**Version:** 1.5-v2 (Production)  
**Last Updated:** January 2026  
**Architecture:** Single LLM Call with Intelligent Video Generation

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Pipeline Flow](#pipeline-flow)
4. [Core Components](#core-components)
5. [API Reference](#api-reference)
6. [Player V2 Specification](#player-v2-specification)
7. [Section Types](#section-types)
8. [Renderer Selection Logic](#renderer-selection-logic)
9. [TTS Integration](#tts-integration)
10. [Video Generation (WAN & Manim)](#video-generation)
11. [Schema Reference](#schema-reference)
12. [Job Management](#job-management)
13. [Error Handling & Resume](#error-handling--resume)
14. [Configuration & Environment](#configuration--environment)
15. [Analytics & Metrics](#analytics--metrics)

---

## Executive Summary

The V2 Pipeline is a **Deterministic Educational Film Engine** that converts PDF/document chapters into pedagogically structured, animated explanation videos with synchronized narration. 

### Key Achievements
- **95% reduction in LLM calls** - Entire presentation generated in single API call (~150s)
- **TEACH → SHOW pattern** - Content explains concepts first, then shows video demonstrations
- **Intelligent video selection** - LLM decides when to generate videos based on subject matter
- **Two-channel separation** - Display content (screen) ≠ Narration (audio)
- **Decision logging** - All LLM decisions captured for analysis

### Technology Stack
| Component | Technology |
|-----------|------------|
| Backend | Python 3.11 + Flask |
| Frontend Player | Vanilla JavaScript (player_v2.js) |
| LLM | OpenRouter (Gemini 2.5 Pro) |
| TTS | Edge TTS (en-IN-PrabhatNeural) |
| Video Generation | Kie.ai WAN API |
| Animation | Manim (math/physics) |
| Document Processing | Datalab API |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           V2 UNIFIED PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────────────┐                 │
│  │ PDF/DOC  │───>│   Datalab   │───>│ Markdown + Images   │                 │
│  │  Upload  │    │  Converter  │    │   Extraction        │                 │
│  └──────────┘    └─────────────┘    └──────────┬──────────┘                 │
│                                                 │                            │
│                                                 ▼                            │
│                  ┌──────────────────────────────────────────┐               │
│                  │     V2 UNIFIED CONTENT GENERATOR         │               │
│                  │     (Single LLM Call - ~150 seconds)     │               │
│                  │                                          │               │
│                  │  • Section structure generation          │               │
│                  │  • Narration text for each segment       │               │
│                  │  • Visual content specifications         │               │
│                  │  • Display directives (TEACH/SHOW)       │               │
│                  │  • Video/Manim prompt generation         │               │
│                  │  • Quiz extraction & formatting          │               │
│                  │  • Decision logging                      │               │
│                  └──────────────────────────────────────────┘               │
│                                                 │                            │
│                                                 ▼                            │
│                  ┌──────────────────────────────────────────┐               │
│                  │      TRANSFORM TO PLAYER SCHEMA          │               │
│                  │      (presentation.json format)          │               │
│                  └──────────────────────────────────────────┘               │
│                                                 │                            │
│                    ┌────────────┬───────────────┼───────────┬────────────┐  │
│                    ▼            ▼               ▼           ▼            ▼  │
│              ┌──────────┐ ┌──────────┐  ┌────────────┐ ┌─────────┐ ┌──────┐│
│              │ Duration │ │   TTS    │  │   Manim    │ │   WAN   │ │Image ││
│              │ Estimate │ │Generation│  │  CodeGen   │ │  Video  │ │ Link ││
│              │ (~150WPM)│ │(Edge TTS)│  │ (Sonnet 4) │ │(Kie.ai) │ │      ││
│              └──────────┘ └──────────┘  └────────────┘ └─────────┘ └──────┘│
│                    │            │               │           │            │  │
│                    └────────────┴───────────────┼───────────┴────────────┘  │
│                                                 ▼                            │
│                         ┌────────────────────────────────────┐              │
│                         │       presentation.json            │              │
│                         │    + audio/ + videos/ + images/    │              │
│                         └────────────────────────────────────┘              │
│                                                 │                            │
│                                                 ▼                            │
│                         ┌────────────────────────────────────┐              │
│                         │         PLAYER V2 (Browser)        │              │
│                         │    player_v2.js + player_v2.css    │              │
│                         └────────────────────────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Architectural Principles

1. **PLAYER IS DUMB** - The player executes JSON instructions without determining layout, timing, or pedagogy
2. **ONE PRIMARY ATTENTION LAYER AT A TIME** - Text or visuals are prominent, not both simultaneously
3. **TEACH → THEN SHOW** - Narration explains concepts, then visuals reinforce
4. **EVERYTHING IS TIMED** - All segments have precise, synchronized durations
5. **TWO-CHANNEL SEPARATION** - Narration is audio-only; display_text is screen display only
6. **FAIL-FAST POLICY** - Strict fail-fast behavior with no fallbacks for critical components

---

## Pipeline Flow

### Phase-by-Phase Execution

```
PHASE 1: Document Conversion
├── Input: PDF/DOC/DOCX/ODT file
├── Processor: Datalab API
├── Output: Markdown text + extracted images (base64)
└── Duration: 5-15 seconds

PHASE 2: Image Processing
├── Input: Base64 images from Datalab
├── Processor: Green screen application
├── Output: Processed images in job/images/
└── Duration: 1-5 seconds

PHASE 3: LLM Generation (SINGLE CALL)
├── Input: Markdown content + images list + subject/grade
├── Processor: OpenRouter API (Gemini 2.5 Pro)
├── System Prompt: UNIFIED_SYSTEM_PROMPT (comprehensive)
├── Output: Complete presentation structure with all sections
├── Model Config:
│   ├── Temperature: 0.7
│   ├── Max Tokens: 32,000
│   └── Timeout: 300 seconds
└── Duration: 120-180 seconds

PHASE 4: Schema Transformation
├── Input: Raw LLM output
├── Processor: transform_to_player_schema()
├── Output: Player-compatible presentation.json structure
└── Duration: <1 second

PHASE 5: Duration Estimation
├── Input: Narration text per segment
├── Formula: word_count / 2.5 (150 WPM), minimum 3 seconds
├── Output: duration_estimate per segment
└── Duration: <1 second

PHASE 6: TTS Generation
├── Input: Segment narration text
├── Processor: Edge TTS (en-IN-PrabhatNeural)
├── Output: Audio files in job/audio/
├── Note: Duration already calculated programmatically in Phase 5
└── Duration: 30-120 seconds (parallel processing)

PHASE 7: Image Linking
├── Input: Saved images + visual_content references
├── Processor: _link_images_to_presentation()
├── Output: image_path fields populated in segments
└── Duration: <1 second

PHASE 8: Validation
├── Input: Complete presentation
├── Processor: enforce_renderer_policy()
├── Checks: Renderer restrictions, prompt lengths
└── Duration: <1 second

PHASE 9: Manim Code Generation
├── Input: Sections with renderer="manim"
├── Processor: ManimCodeGenerator (Claude Sonnet 4)
├── Output: Python Manim code embedded in sections
└── Duration: 10-60 seconds per section

PHASE 10: WAN Prompt Validation
├── Input: video_prompts from sections
├── Validator: validate_video_prompts()
├── Check: 80+ word minimum per prompt
└── Duration: <1 second

PHASE 11: Video Rendering
├── Input: Video prompts + Manim code
├── Processors:
│   ├── WAN (Kie.ai): Biology, processes, organisms
│   └── Manim: Equations, graphs, geometry
├── Output: Video files in job/videos/
└── Duration: 60-300 seconds (depends on video count)

PHASE 12: Finalization
├── Save presentation.json
├── Save analytics.json
├── Update job status to "completed"
└── Duration: <1 second
```

---

## Core Components

### 1. Unified Content Generator (`core/unified_content_generator.py`)

The heart of V2 - generates complete presentation in a single LLM call.

```python
# Key Functions

def generate_presentation(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    config: GeneratorConfig = None
) -> dict:
    """
    Generate complete presentation from raw markdown with retry.
    Returns complete presentation dict ready for transformation.
    """

def transform_to_player_schema(
    v2_output: dict,
    subject: str = "Science",
    grade: str = "10"
) -> dict:
    """
    Transform V2 LLM output to final presentation.json format.
    Adds fields for TTS, Manim, video paths, etc.
    """

def call_openrouter_llm(
    system_prompt: str,
    user_prompt: str,
    config: GeneratorConfig
) -> Tuple[str, dict]:
    """
    Call OpenRouter API with retry logic.
    Returns (response_text, usage_stats).
    """
```

**Generator Configuration:**
```python
@dataclass
class GeneratorConfig:
    model: str = "google/gemini-2.5-pro-preview"
    temperature: float = 0.7
    max_tokens: int = 32000
    max_retries: int = 3
    retry_delay_base: float = 2.0
    timeout: int = 300
```

### 2. Job Manager (`core/job_manager.py`)

Handles job lifecycle, status tracking, and persistence.

```python
class JobManager:
    def create_job(job_type: str, params: dict) -> str:
        """Create new job, returns job_id (8-char UUID)"""
    
    def update_job(job_id: str, updates: dict, persist: bool = True):
        """Update job status/progress"""
    
    def get_job(job_id: str) -> dict:
        """Get job details"""
    
    def complete_job(job_id: str, result: dict):
        """Mark job as completed"""
    
    def fail_job(job_id: str, error: str):
        """Mark job as failed with error message"""
```

**Job Status States:**
- `queued` - Job created, waiting to start
- `processing` - Job actively running
- `completed` - Job finished successfully
- `failed` - Job encountered error

### 3. TTS Duration Service (`core/tts_duration.py`)

Generates audio files. Duration is calculated programmatically from word count (~150 WPM).

```python
def update_durations_simplified(
    presentation: dict,
    output_dir: Path,
    production_provider: str = "edge"
) -> dict:
    """
    Generate TTS audio for all segments.
    Duration is calculated programmatically: word_count / 2.5 (~150 WPM).
    Returns modified presentation with audio_path fields.
    """
```

**TTS Provider:**
| Provider | Voice | Use Case |
|----------|-------|----------|
| Edge TTS | en-IN-PrabhatNeural | Production (Indian male) |

**Duration Calculation:**
- Formula: `word_count / 2.5` (~150 words per minute)
- Minimum: 3 seconds per segment
- No MP3 measurement - purely programmatic estimation

### 4. Renderer Executor (`core/renderer_executor.py`)

Orchestrates video generation (Manim + WAN).

```python
def render_all_topics(
    presentation: dict,
    output_dir: str,
    dry_run: bool = False,
    skip_wan: bool = False,
    output_dir_base: str = None
) -> List[dict]:
    """
    Render all video content for presentation.
    Returns list of render results with paths.
    """
```

---

## API Reference

### Submit Job

**Endpoint:** `POST /submit_job`

**Content-Type:** `multipart/form-data` (file upload) or `application/json`

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| file | File | - | PDF/DOC/DOCX/ODT/MD file |
| subject | string | "General Science" | Subject area |
| grade | string | "9" | Grade level |
| pipeline_version | string | "v15" | `v15_v2` for V2 pipeline |
| dry_run | boolean | false | Skip video/audio generation |
| skip_wan | boolean | false | Skip WAN video generation |
| skip_avatar | boolean | false | Skip avatar video |
| tts_provider | string | "edge" | TTS provider |

**Response:**
```json
{
  "status": "accepted",
  "job_id": "19a222e7",
  "dry_run": false,
  "skip_wan": false,
  "content_preview": "First 300 chars of content...",
  "message": "Job submitted successfully. Poll /job/<job_id>/status for progress."
}
```

### Job Status

**Endpoint:** `GET /job/<job_id>/status`

**Response:**
```json
{
  "job_id": "19a222e7",
  "status": "processing",
  "progress": 65,
  "current_step": "Generating TTS audio",
  "current_phase": "tts_generation",
  "status_message": "Creating narration audio files...",
  "steps_completed": 5,
  "total_steps": 11,
  "created_at": "2026-01-02T10:30:00",
  "started_at": "2026-01-02T10:30:01",
  "completed_at": null,
  "error": null
}
```

### Job Retry/Resume

**Endpoint:** `POST /job/<job_id>/retry`

Retries a failed or stuck job. Marks "processing" jobs as "failed" first, then restarts.

### List Jobs

**Endpoint:** `GET /jobs`

Returns list of all jobs with status summary.

### Dashboard

**Endpoint:** `GET /dashboard`

Returns HTML dashboard for job management UI.

---

## Player V2 Specification

### File Structure
```
player/
├── player_v2.html      # Main HTML template
├── player_v2.js        # JavaScript player logic (1882 lines)
├── player_v2.css       # Styling
└── jobs/
    └── {job_id}/
        ├── index.html          # Baked player copy
        ├── player_v2.js        # Baked player copy
        ├── player_v2.css       # Baked player copy
        ├── presentation.json   # Presentation data
        ├── audio/              # TTS audio files
        ├── videos/             # Generated videos
        └── images/             # Extracted images
```

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 0: BACKGROUND (gradient/color)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────┐  ┌───────────────────────────┐│
│  │      LAYER 1: CONTENT        │  │    LAYER 2: AVATAR       ││
│  │         (70% width)          │  │      (55% width)         ││
│  │                              │  │      (85% height)        ││
│  │  • Text/Paragraphs           │  │                          ││
│  │  • Bullet Lists              │  │   ┌──────────────────┐   ││
│  │  • Equations (MathJax)       │  │   │  Chroma-keyed    │   ││
│  │  • Images/Diagrams           │  │   │  Avatar Video    │   ││
│  │  • Quiz Cards                │  │   │  (Green screen   │   ││
│  │  • Flashcards                │  │   │   removed)       │   ││
│  │                              │  │   └──────────────────┘   ││
│  └──────────────────────────────┘  └───────────────────────────┘│
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │              LAYER 3: VIDEO OVERLAY (65% width)              ││
│  │            (appears during SHOW phase, hides content)        ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Display Directives

Display directives control layer visibility per segment:

```json
{
  "display_directives": {
    "text_layer": "show|dim|hide",
    "visual_layer": "show|hide",
    "avatar_layer": "show"
  }
}
```

**TEACH → SHOW Pattern:**

| Phase | text_layer | visual_layer | Description |
|-------|------------|--------------|-------------|
| TEACH | show | hide | Text/bullets visible, avatar narrates |
| SHOW | hide | show | Video plays, content hidden |

### Progressive Reveal

Content reveals progressively as audio plays:

1. Audio `timeupdate` event fires
2. Calculate current segment from cumulative durations
3. Highlight current segment (`segment-active` class)
4. Dim previous segments
5. For video sections: switch beat video at segment boundaries

---

## Section Types

### 1. Intro Section
```json
{
  "section_type": "intro",
  "title": "Welcome",
  "renderer": "none",
  "display_directives": {
    "text_layer": "hide",
    "visual_layer": "hide",
    "avatar_layer": "show"
  }
}
```
- Avatar only, no content on screen
- Welcome message and lesson introduction

### 2. Summary Section
```json
{
  "section_type": "summary",
  "title": "Learning Objectives",
  "renderer": "none",
  "visual_beats": [
    {
      "visual_type": "bullet_list",
      "display_text": "• Objective 1\n• Objective 2"
    }
  ]
}
```
- Always uses `bullet_list` visual type
- Checkmarks (✓) as bullet markers

### 3. Content Section
```json
{
  "section_type": "content",
  "title": "Topic Name",
  "renderer": "video|manim|none",
  "narration": {
    "segments": [
      {
        "segment_id": "seg_1",
        "text": "Narration for audio...",
        "display_directives": {"text_layer": "show"},
        "visual_content": {
          "content_type": "paragraph",
          "verbatim_text": "Display text from PDF..."
        }
      },
      {
        "segment_id": "seg_2",
        "text": "Describing what we see...",
        "display_directives": {"text_layer": "hide", "visual_layer": "show"}
      }
    ]
  },
  "video_prompts": [
    {
      "segment_id": "seg_2",
      "prompt": "80+ word video prompt...",
      "duration_hint": 12
    }
  ]
}
```

### 4. Example Section
```json
{
  "section_type": "example",
  "title": "Worked Example",
  "renderer": "manim"
}
```
- Optional, only if examples exist in source
- Often uses Manim for step-by-step solutions

### 5. Quiz Section
```json
{
  "section_type": "quiz",
  "title": "Practice Questions",
  "quiz_data": {
    "questions": [
      {
        "question": "Question text?",
        "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
        "correct_answer": "B",
        "explanation": "Why B is correct..."
      }
    ]
  },
  "narration": {
    "segments": [
      {"segment_id": "seg_1", "text": "Read question...", "question_index": 0, "purpose": "introduce"},
      {"segment_id": "seg_2", "text": "Think about it...", "question_index": 0, "purpose": "emphasize"},
      {"segment_id": "seg_3", "text": "The answer is...", "question_index": 0, "purpose": "explain"}
    ]
  }
}
```
- Progressive reveal: question → pause → answer
- 3 segments per question (introduce/emphasize/explain)
- Splits into multiple sections if >8 questions

### 6. Memory Section
```json
{
  "section_type": "memory",
  "title": "Key Concepts Review",
  "flashcards": [
    {"front": "Term", "back": "Definition"},
    {"front": "Concept", "back": "Explanation"}
  ]
}
```
- 3-5 flashcard-style key concepts
- Single section

### 7. Recap Section
```json
{
  "section_type": "recap",
  "title": "Visual Summary",
  "renderer": "video",
  "video_prompts": [
    {"segment_id": "seg_1", "prompt": "80+ word scene 1...", "duration_hint": 12},
    {"segment_id": "seg_2", "prompt": "80+ word scene 2...", "duration_hint": 12},
    {"segment_id": "seg_3", "prompt": "80+ word scene 3...", "duration_hint": 12},
    {"segment_id": "seg_4", "prompt": "80+ word scene 4...", "duration_hint": 12},
    {"segment_id": "seg_5", "prompt": "80+ word scene 5...", "duration_hint": 12}
  ],
  "recap_video_paths": [
    "videos/recap_beat_1.mp4",
    "videos/recap_beat_2.mp4",
    "videos/recap_beat_3.mp4",
    "videos/recap_beat_4.mp4",
    "videos/recap_beat_5.mp4"
  ]
}
```
- ALWAYS exactly 5 video scenes
- Full-screen video mode (content hidden)
- Cinematic story-style narration

---

## Renderer Selection Logic

### Subject-Based Renderer Selection

| Subject | Renderer | Use Case | Examples |
|---------|----------|----------|----------|
| Biology | video (WAN) | Anatomy, processes, organisms | Neurons, cells, digestion |
| Physics | video/manim | Phenomena (video), equations (manim) | Motion, waves, formulas |
| Math | manim | Equations, graphs, geometry | Quadratic formula, parabolas |
| Chemistry | video/manim | Reactions (video), formulas (manim) | Combustion, molecular bonds |

### Decision Logging

Every section includes decision reasoning:

```json
{
  "decision_log": {
    "total_video_prompts": 8,
    "total_manim_specs": 2,
    "renderer_choices": [
      {
        "section_id": "section_3",
        "section_title": "The Nervous System",
        "renderer": "video",
        "reason": "Biology content about neurons and synapses requires anatomical visualization for student understanding"
      }
    ],
    "content_analysis": "Chapter covers nervous system anatomy with diagrams of neurons and reflex arcs"
  }
}
```

---

## TTS Integration

### Edge TTS Configuration

```python
# Voice: Indian English Male
EDGE_TTS_VOICE = "en-IN-PrabhatNeural"

# Async audio generation
async def generate_edge_tts(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
    await communicate.save(output_path)
```

### Duration Calculation (Programmatic)

Duration is calculated **programmatically from word count**, NOT measured from generated MP3 files:

```python
def calculate_duration(text: str) -> float:
    """
    Calculate segment duration from word count.
    Uses ~150 WPM (words per minute) speaking rate.
    """
    word_count = len(text.split())
    duration = word_count / 2.5  # 150 WPM = 2.5 words/second
    return max(duration, 3.0)    # Minimum 3 seconds
```

**Key Points:**
- **Formula:** `word_count / 2.5` (~150 words per minute)
- **Minimum:** 3 seconds per segment
- **No audio measurement:** Duration is estimated before TTS generation
- **Sync accuracy:** Player uses these programmatic durations for audio-visual sync

### Audio File Naming

```
audio/section_{section_id}_seg_{segment_id}.mp3
```

Example: `audio/section_3_seg_2.mp3`

---

## Video Generation

### WAN Video (Kie.ai API)

**Endpoint:** Kie.ai WAN API

**Requirements:**
- Minimum 80 words per video prompt
- Duration: 10-15 seconds per video
- Max polling: 120 attempts

**Prompt Structure:**
```
{scene description} + {camera movement} + {lighting/style} + {duration hint}
```

**Example:**
```
Cinematic 3D animation inside the human nervous system showing a detailed 
neuron cell with its soma glowing softly blue, multiple branching dendrites 
receiving signals visualized as tiny sparks, the electrical impulse 
consolidates and travels down the long axon as a bright wave of energy, 
passing through the myelin sheath segments which appear as translucent 
white bands, the signal reaches the axon terminals and triggers the release 
of neurotransmitter molecules shown as small glowing spheres crossing the 
synaptic cleft to the next neuron, scientific documentary style with dark 
purple background, smooth camera movement following the signal, duration 
12 seconds
```

### Manim Code Generation

**Model:** Claude Sonnet 4 via OpenRouter

**Process:**
1. Extract manim_spec from section
2. Generate Python Manim code
3. Validate syntax
4. Embed code in section for later execution

**Output Format:**
```python
from manim import *

class TopicAnimation(Scene):
    def construct(self):
        # Generated animation code
        equation = MathTex(r"x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}")
        self.play(Write(equation))
        self.wait(2)
```

---

## Schema Reference

### presentation.json

```json
{
  "spec_version": "v1.5",
  "title": "Lesson Title",
  "subject": "Biology",
  "grade": "10",
  "avatar_global": {
    "style": "teacher",
    "default_position": "right",
    "default_width_percent": 52,
    "gesture_enabled": true
  },
  "metadata": {
    "generated_by": "v1.5-v2-unified",
    "llm_calls": 1,
    "llm_time_seconds": 145.23,
    "dry_run": false
  },
  "decision_log": {
    "total_video_prompts": 8,
    "total_manim_specs": 0,
    "renderer_choices": [],
    "content_analysis": "..."
  },
  "sections": [
    {
      "section_id": 1,
      "section_type": "intro|summary|content|example|quiz|memory|recap",
      "title": "Section Title",
      "renderer": "none|manim|video",
      "decision_reason": "Why this renderer was chosen",
      "avatar_layout": {
        "visibility": "always",
        "mode": "floating",
        "position": "right|center",
        "width_percent": 52
      },
      "narration": {
        "full_text": "Complete section narration...",
        "total_duration_seconds": 45.5,
        "audio_path": "audio/section_1.mp3",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Segment narration text...",
            "purpose": "introduce|explain|emphasize|transition|conclude",
            "duration_estimate": 8.5,
            "duration_seconds": 8.7,
            "audio_path": "audio/section_1_seg_1.mp3",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            },
            "visual_content": {
              "content_type": "paragraph|bullet_list|equation|image|diagram",
              "verbatim_text": "Display content...",
              "bullet_points": [],
              "formulas": [],
              "image_path": null
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_beat_type": "text|bullet_list|equation|diagram|image|video",
          "display_text": "...",
          "latex_content": null,
          "image_id": null,
          "video_asset": null
        }
      ],
      "display_directives": {},
      "video_prompts": [],
      "quiz_data": null,
      "flashcards": null,
      "video_path": null,
      "beat_video_paths": [],
      "recap_video_paths": []
    }
  ]
}
```

### analytics.json

```json
{
  "status": "completed",
  "pipeline_time_seconds": 342.5,
  "llm_time_seconds": 145.2,
  "llm_input_tokens": 12500,
  "llm_output_tokens": 8200,
  "llm_total_tokens": 20700,
  "llm_model": "google/gemini-2.5-pro-preview",
  "llm_cost_usd": 0.0976,
  "tts_segments": 45,
  "tts_count": 45,
  "tts_duration_seconds": 320.5,
  "tts_time_seconds": 85.3,
  "manim_sections": 0,
  "manim_success": 0,
  "manim_failed": 0,
  "manim_videos": 0,
  "manim_time_seconds": 0,
  "wan_videos": 8,
  "wan_time_seconds": 180.5,
  "wan_success": 8,
  "wan_failed": 0,
  "image_count": 3,
  "table_count": 2,
  "qa_pair_count": 8,
  "sections": 11,
  "segments": 45,
  "total_duration_seconds": 320.5,
  "phases": [
    {"phase": "llm_generation", "duration_seconds": 145.2, "tokens": 20700, "cost_usd": 0.0976},
    {"phase": "tts_generation", "duration_seconds": 85.3, "segments": 45, "audio_duration": 320.5},
    {"phase": "video_render", "duration_seconds": 180.5, "wan_videos": 8, "manim_rendered": 0, "failed": 0}
  ]
}
```

---

## Job Management

### Job Folder Structure

```
player/jobs/{job_id}/
├── index.html              # Baked player (standalone)
├── player_v2.js
├── player_v2.css
├── presentation.json       # Main presentation data
├── analytics.json          # Pipeline metrics
├── source_markdown.md      # Original content
├── audio/
│   ├── section_1_seg_1.mp3
│   ├── section_1_seg_2.mp3
│   └── ...
├── videos/
│   ├── recap_beat_1.mp4
│   ├── recap_beat_2.mp4
│   └── ...
└── images/
    ├── image_001.png
    └── ...
```

### Job Index

Jobs are indexed in `player/jobs/jobs_index.json`:

```json
{
  "19a222e7": {
    "id": "19a222e7",
    "type": "v15_v2_pipeline",
    "status": "completed",
    "params": {
      "subject": "Biology",
      "grade": "10",
      "source_file": "chapter5.pdf"
    },
    "progress": 100,
    "created_at": "2026-01-02T10:30:00",
    "completed_at": "2026-01-02T10:35:42"
  }
}
```

---

## Error Handling & Resume

### Retry Logic

The pipeline implements exponential backoff retry:

```python
for attempt in range(config.max_retries):
    try:
        response = call_api()
        break
    except (JSONParseError, SchemaValidationError) as e:
        delay = config.retry_delay_base * (2 ** attempt)
        time.sleep(delay)
```

### Job Resume

Jobs can be resumed after server restart:

**Endpoint:** `POST /job/{job_id}/retry`

**Behavior:**
1. Check if job is in "processing" state (stuck)
2. Mark as "failed" if stuck
3. Re-queue job with same parameters
4. Resume from failed phase (WAN videos continue from last successful)

### WAN Session Reset

Each job starts with fresh WAN hash cache:

```python
from render.wan.wan_runner import reset_wan_session
reset_wan_session()  # Prevents cross-job duplicate detection
```

---

## Configuration & Environment

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM | Yes |
| `DATALAB_API_KEY` | Datalab API for PDF conversion | Yes |
| `KIE_API_KEY` | Kie.ai API for WAN video | For video |
| `SESSION_SECRET` | Flask session secret | Yes |

### Server Configuration

```python
# Flask app binds to port 5000
app.run(host='0.0.0.0', port=5000)
```

### Deployment

**Recommended:** VM deployment (not autoscale)
- Background video rendering requires persistent process
- Jobs can be interrupted by autoscale cold starts

---

## Analytics & Metrics

### Key Performance Indicators

| Metric | Target | Description |
|--------|--------|-------------|
| LLM Time | <180s | Single LLM call duration |
| Total Pipeline Time | <600s | End-to-end processing |
| LLM Cost | <$0.15 | Per presentation |
| Video Success Rate | >95% | WAN video generation |
| TTS Success Rate | 100% | Audio generation |

### Cost Breakdown (Gemini 2.5 Pro)

```
Input tokens:  ~12,000 × $1.25/M = $0.015
Output tokens: ~8,000 × $10.00/M = $0.080
-----------------------------------------
Total LLM cost per presentation: ~$0.10
```

### Monitoring

Analytics are saved per job in `analytics.json` with:
- Phase-by-phase timing breakdown
- Token usage and costs
- Success/failure counts
- Total duration metrics

---

## Appendix: OpenRouter API Call

```python
# api/app.py uses OPENROUTER_API_KEY environment variable
# core/unified_content_generator.py line 18

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://replit.com",
    "X-Title": "AI Education V2"
}

payload = {
    "model": "google/gemini-2.5-pro-preview",
    "messages": [
        {"role": "system", "content": UNIFIED_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.7,
    "max_tokens": 32000
}

response = requests.post(
    f"{OPENROUTER_BASE_URL}/chat/completions",
    headers=headers,
    json=payload,
    timeout=300
)
```

---

*Document generated for AI Animated Education V2 Pipeline*
