# V3 Per-Question Quiz Implementation Changes

**Date:** 2026-03-20  
**Status:** Implemented  
**Files Modified:** 3  
**Backup Files:** 3 (.backup)

---

## Overview

Implemented support for `section.renderer = "per_question"` in the V3 pipeline. This allows quiz sections where each question's `explanation_visual` can have an independently-decided renderer (manim, image_to_video, text_to_video, etc.).

---

## Changes by File

### 1. `core/pipeline_v3.py`

**Change 1: Line ~579 - Added "per_question" to video_sections detection**

```python
# BEFORE:
if s.get("renderer") in ("video", "text_to_video", "image_to_video")

# AFTER:
if s.get("renderer") in ("video", "text_to_video", "image_to_video", "per_question")
```

**Change 2: Lines ~640-710 - New section to process per_question quiz sections**

Added a new processing block after the existing video generation section:

```python
# V3: Handle per_question quiz sections - each question has its own explanation_visual renderer
per_question_sections = [
    s for s in video_sections if s.get("renderer") == "per_question"
]
if per_question_sections and not skip_wan:
    log("wan_video", f"Starting per_question quiz explanation_visual generation...")
    try:
        from core.renderer_executor import execute_renderer
        
        total_processed = 0
        for section in per_question_sections:
            section_id = section.get("section_id", "?")
            questions = section.get("questions", [])
            
            for qi, question in enumerate(questions):
                q_id = question.get("question_id", f"q{qi + 1}")
                exp_visual = question.get("explanation_visual", {})
                exp_renderer = exp_visual.get("renderer", "")
                
                if not exp_renderer or exp_renderer == "none":
                    continue
                
                # Process the explanation_visual using execute_renderer
                result = execute_renderer(
                    topic=exp_visual,
                    output_dir=str(output_path / "videos"),
                    dry_run=False,
                    skip_wan=False,
                    video_provider=video_provider,
                )
                
                if result.get("status") == "success":
                    video_path = result.get("video_path", "")
                    question["explanation_visual_video_path"] = video_path
                    total_processed += 1
```

---

### 2. `core/renderer_executor.py`

**Change 1: Lines ~444-466 - Updated function docstring and added top-level renderer detection**

```python
# BEFORE:
def execute_renderer(topic: dict, ...) -> dict:
    """
    V3 Section-Level Renderer Executor.
    Routing priority:
    1. render_spec.renderer
    2. render_spec.segment_specs[]
    3. Legacy fallbacks
    """
    ...
    render_spec = topic.get("render_spec") or {}
    renderer = render_spec.get("renderer")
    renderer_reason = render_spec.get("renderer_reason", "")

# AFTER:
def execute_renderer(topic: dict, ...) -> dict:
    """
    V3 Section-Level Renderer Executor.
    Routing priority:
    1. render_spec.renderer
    2. render_spec.segment_specs[]
    3. Legacy fallbacks
    4. explanation_visual structure: renderer at top level
    """
    ...
    render_spec = topic.get("render_spec") or {}
    renderer = render_spec.get("renderer")
    
    # Check top-level renderer (for explanation_visual structure)
    if not renderer:
        renderer = topic.get("renderer", "")
    
    renderer_reason = render_spec.get("renderer_reason", "") or topic.get("renderer_reason", "")
```

**Change 2: Lines ~526-533 - Support for image_to_video_beats at top level**

```python
# BEFORE:
manim_scene_spec = render_spec.get("manim_scene_spec")
video_prompts = render_spec.get("video_prompts") or topic.get("video_prompts", [])
has_v12_specs = bool(manim_scene_spec) or bool(video_prompts)

# AFTER:
manim_scene_spec = render_spec.get("manim_scene_spec") or topic.get("manim_scene_spec", "")
video_prompts = render_spec.get("video_prompts") or topic.get("video_prompts", [])
image_to_video_beats = topic.get("image_to_video_beats", [])
has_v12_specs = bool(manim_scene_spec) or bool(video_prompts) or bool(image_to_video_beats)
```

**Change 3: Lines ~656-690 - Added support for image_to_video_beats[] in image_to_video renderer**

```python
# Added new elif block after video_prompts handling:
elif image_to_video_beats and isinstance(image_to_video_beats, list):
    # EXPLANATION_VISUAL FORMAT: image_to_video_beats[] from quiz explanation_visual
    beats = []
    for i, beat in enumerate(image_to_video_beats):
        img_start = beat.get("image_prompt_start", "")
        img_end = beat.get("image_prompt_end", "")
        image_prompt = f"{img_start}" if not img_end else f"{img_start} Then transition to: {img_end}"
        beats.append({
            "beat_id": beat.get("beat_id", f"beat_{i + 1}"),
            "beat_idx": i,
            "image_prompt": image_prompt,
            "prompt": beat.get("video_prompt", ""),
            "duration": beat.get("duration", 15),
        })
```

---

### 3. `core/v3_validator.py`

**Change 1: Lines ~48-60 - Added "per_question" to VALID_RENDERERS**

```python
# BEFORE:
VALID_RENDERERS = {
    "manim", "video", "none", "wan", "wan_video",
    "image_to_video", "text_to_video", "infographic", "image", "threejs",
}

# AFTER:
VALID_RENDERERS = {
    "manim", "video", "none", "wan", "wan_video",
    "image_to_video", "text_to_video", "infographic", "image", "threejs",
    "per_question",
}
```

**Change 2: Lines ~318-324 - Updated _check_quiz_section() detection**

```python
# BEFORE:
def _check_quiz_section(section: dict) -> List[V3ValidatorError]:
    """Quiz sections must have 4 narration scripts per question for 4 avatar clips."""
    ...
    if section_type != "quiz":
        return errors

# AFTER:
def _check_quiz_section(section: dict) -> List[V3ValidatorError]:
    """Quiz sections must have 4 narration scripts per question for 4 avatar clips."""
    ...
    section_renderer = section.get("renderer", "")
    # Quiz sections can have section_type="quiz" or renderer="per_question"
    if section_type != "quiz" and section_renderer != "per_question":
        return errors
```

**Change 3: Lines ~362-435 - Added explanation_visual validation in _check_quiz_section()**

Added comprehensive validation for quiz question explanation_visual blocks:

```python
# Validate explanation_visual for per_question quiz sections
exp_visual = q.get("explanation_visual", {})
if not exp_visual:
    errors.append(V3ValidatorError("v3_quiz_missing_explanation_visual", ...))
else:
    # Validate renderer field
    exp_renderer = exp_visual.get("renderer", "")
    if not exp_renderer:
        errors.append(V3ValidatorError("v3_quiz_explanation_visual_missing_renderer", ...))
    elif exp_renderer not in ("manim", "image_to_video", "text_to_video", "infographic", "image", "none"):
        errors.append(V3ValidatorError("v3_quiz_explanation_visual_invalid_renderer", ...))
    
    # Validate renderer_reason
    exp_reason = exp_visual.get("renderer_reason", "")
    if not exp_reason:
        errors.append(V3ValidatorError("v3_quiz_explanation_visual_missing_renderer_reason", ...))
    
    # Validate spec based on renderer type
    if exp_renderer == "manim":
        if not exp_visual.get("manim_scene_spec"):
            errors.append(...)
    elif exp_renderer == "image_to_video":
        if not exp_visual.get("image_to_video_beats"):
            errors.append(...)
    elif exp_renderer == "text_to_video":
        if not exp_visual.get("video_prompt"):
            errors.append(...)
```

---

## What This Enables

1. **Per-Question Renderer Decisions**: Each quiz question can have its own `explanation_visual.renderer` (manim, image_to_video, text_to_video, etc.)

2. **Flexible Visualization**: Different questions in the same quiz can display different visualization types:
   - Manim for math/formula explanations
   - image_to_video for biological diagrams
   - text_to_video for narrative explanations

3. **Clean Contract**: Section carries `renderer="per_question"` signal, and pipeline knows to look inside each question for its own renderer

4. **Full Pipeline Support**:
   - Director generates quiz sections with per_question renderer
   - Validator validates explanation_visual structure
   - Pipeline processes each question's visual independently
   - Renderer executor handles all renderer types

---

## Backup Files

- `core/pipeline_v3.py.backup`
- `core/renderer_executor.py.backup`
- `core/v3_validator.py.backup`

---

## Testing

All modified files pass Python syntax validation:
```bash
python3 -m py_compile core/pipeline_v3.py
python3 -m py_compile core/renderer_executor.py
python3 -m py_compile core/v3_validator.py
```

---

## Related Files (Not Modified)

- `core/prompts/director_v3_partition_prompt.txt` - Defines the per_question quiz schema (already had the spec)
- `core/quiz_card_generator.py` - Generates quiz card HTML/JS (no changes needed)
