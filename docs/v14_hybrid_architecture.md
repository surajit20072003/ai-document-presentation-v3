# V1.4 Hybrid Pipeline Architecture

## Overview

The V1.4 Hybrid Pipeline uses **Split Directors** (Content Director + Recap Director) for easier LLM generation, while keeping the proven V1.3 rendering infrastructure unchanged. The **Merge Step** converts Split Director output into player-compatible format.

## Design Principle

> **"Only change the LLM layer - display will display"**

The player expects a specific JSON structure. We don't change the player. Instead:
1. LLM layer generates smaller, easier sections (5 separate recap_scene_N)
2. Merge Step converts them into player-compatible format (1 recap section)
3. Player layer receives exactly what it expects

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT: markdown_content, subject, grade                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ PASS 0: Smart Chunker (core/smart_chunker.py)                   │
│   Function: call_smart_chunker(markdown_content, subject,       │
│             tracker, max_retries)                               │
│   Output: {source_topic, topics: [{topic_id, title, ...}]}      │
└─────────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────────────┐
│ PASS 1a: Content Dir    │    │ PASS 1b: Recap Director         │
│ (content_director.py)   │    │ (recap_director.py)             │
│                         │    │                                 │
│ Input:                  │    │ Input:                          │
│   topics: List[Dict]    │    │   full_markdown: str (original) │
│   subject: str          │    │   subject: str                  │
│   grade: str            │    │   grade: str                    │
│                         │    │                                 │
│ Output:                 │    │ Output:                         │
│   {title, sections: [   │    │   {sections: [                  │
│     intro,              │    │     memory,                     │
│     summary,            │    │     recap_scene_1,              │
│     content,            │    │     recap_scene_2,              │
│     example,            │    │     recap_scene_3,              │
│     quiz                │    │     recap_scene_4,              │
│   ]}                    │    │     recap_scene_5               │
│                         │    │   ]}                            │
└─────────────────────────┘    └─────────────────────────────────┘
            │                               │
            └───────────────┬───────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ MERGE STEP (core/merge_step.py) - Pure Python, NO LLM          │
│   Function: merge_director_outputs(content_output, recap_output,│
│             subject, grade)                                     │
│                                                                 │
│   CRITICAL TRANSFORMATION:                                      │
│   - 5 recap_scene_N sections → 1 recap section                  │
│   - Preserves player compatibility                              │
│                                                                 │
│   Output Order:                                                 │
│   [intro, summary, content..., memory, recap]                   │
│                                                                 │
│   Recap Section Contains:                                       │
│   - section_type: "recap" (not recap_scene_N)                   │
│   - visual_beats: [{scene_id, video_prompt, duration}, ...]     │
│   - recap_scenes: [{scene_id, video_prompt, narration}, ...]    │
│   - narration: merged from all scenes                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ PASS 2: V1.3 Renderer Dispatch (llm_client_v12.py)              │
│   Function: pass2_dispatch_renderers(presentation, tracker)     │
│                                                                 │
│   Routing:                                                      │
│   - intro/summary/memory → Remotion                             │
│   - content/example → Manim or Video (by concept_type)          │
│   - recap → WAN Video (5 scene videos)                          │
│                                                                 │
│   NO CHANGES from V1.3                                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ OUTPUT: presentation.json (player-compatible)                   │
│                                                                 │
│   Sections: [intro, summary, content..., memory, recap]         │
│   Recap: ONE section with visual_beats/recap_scenes arrays      │
│                                                                 │
│   PLAYER RECEIVES EXACTLY V1.3 FORMAT - NO CHANGES NEEDED       │
└─────────────────────────────────────────────────────────────────┘
```

## Function Signatures

### Smart Chunker
```python
call_smart_chunker(
    markdown_content: str,
    subject: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_retries: int = 2
) -> Dict
# Returns: {source_topic: str, topics: List[Dict]}
```

### Content Director
```python
call_content_director(
    topics: List[Dict],           # From chunker.topics
    subject: str,
    grade: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_structural_retries: int = 4,
    max_semantic_retries: int = 2
) -> Dict
# Returns: {title: str, sections: List[Dict]}
```

### Recap Director
```python
call_recap_director(
    full_markdown: str,           # Original markdown, NOT chunked
    subject: str,
    grade: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_structural_retries: int = 2,
    max_semantic_retries: int = 2
) -> Dict
# Returns: {sections: List[Dict]}
```

### Merge Step
```python
merge_director_outputs(
    content_output: Dict,         # From Content Director
    recap_output: Dict,           # From Recap Director
    subject: str,
    grade: str
) -> Dict
# Returns: Complete presentation.json
```

### Hybrid Function
```python
generate_presentation_v14_hybrid(
    markdown_content: str,
    subject: str = "General Science",
    grade: str = "9",
    chapter: str = "",
    use_remotion: bool = True,
    status_callback: Optional[callable] = None
) -> Tuple[Dict, AnalyticsTracker]
```

## Key Files

| Component | File | Purpose |
|-----------|------|---------|
| Smart Chunker | `core/smart_chunker.py` | Extract topics from markdown |
| Content Director | `core/content_director.py` | Generate intro/summary/content/example/quiz |
| Recap Director | `core/recap_director.py` | Generate memory + 5 recap scenes |
| Merge Step | `core/merge_step.py` | Combine outputs, convert recap format |
| Hybrid Function | `core/llm_client_v12.py` | Orchestrate full pipeline |
| Pipeline | `core/pipeline_v12.py` | Entry point with status callbacks |

## Player Compatibility

The player (`player/player.js`) handles these section_types:
- `intro` - Introduction with avatar
- `summary` - Lesson summary
- `content` - Main content
- `example` - Worked examples
- `quiz` - Quiz questions
- `memory` - Flashcards (5 cards)
- `recap` - Video recap (expects visual_beats/recap_scenes array)

The Merge Step ensures `recap` section contains:
```json
{
  "section_type": "recap",
  "visual_beats": [
    {"scene_id": 1, "video_prompt": "...", "duration": 30},
    {"scene_id": 2, "video_prompt": "...", "duration": 30},
    ...
  ],
  "recap_scenes": [
    {"scene_id": 1, "video_prompt": "...", "narration_text": "..."},
    ...
  ]
}
```

## Why Split Directors?

ISS-080 identified that a single Director LLM struggled to generate:
- 5 flashcards with mnemonics
- 5 video prompts (300+ words each)
- All other section content

By splitting into Content Director + Recap Director:
1. Each LLM call has smaller cognitive load
2. Recap Director focuses ONLY on memory + recap scenes
3. Content Director focuses ONLY on teaching sections
4. Both can be retried independently on failure

The Merge Step recombines them into player-compatible format at no LLM cost.
