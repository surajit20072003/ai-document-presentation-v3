# V1.4 Pipeline Test Procedure

## Purpose
Validate that V1.4 Split Director pipeline produces complete, correct output matching V1.3 quality standards.

## Test Input: 5-Topic Multi-Subject Markdown
The standard test uses a markdown file with 5 distinct topics:
1. Biology: Endosymbiotic Theory
2. Mathematics: Fundamental Theorem of Calculus (with LaTeX)
3. Geometry: Sector Area and Cylinder Volume (with LaTeX)
4. Physics: Wave Period and Frequency (with LaTeX)
5. Chemistry: Equilibrium Constant Kc (with LaTeX)

## Expected Output

### Section Count
| Section Type | Expected Count |
|--------------|----------------|
| intro | 1 |
| summary | 1 |
| content | 5 (one per topic) |
| example | 0-1 (optional) |
| quiz | 0 (none in source) |
| memory | 1 (5 flashcards) |
| recap | 1 (5 scenes) |
| **TOTAL** | 9-10 sections |

### Critical Validations

#### 1. Topic Coverage (ISS-098)
- All 5 topics must appear as content sections
- Each content section title must match source topic
- Checklist:
  - [ ] Biology: Endosymbiotic Theory
  - [ ] Mathematics: Fundamental Theorem of Calculus
  - [ ] Geometry: Area of Sector / Cylinder Volume
  - [ ] Physics: Wave Period and Frequency
  - [ ] Chemistry: Equilibrium Constant

#### 2. LaTeX Preservation (ISS-099)
- Formulas must appear in visual_content.formula or manim_scene_spec
- Checklist:
  - [ ] Integral: `\int_{a}^{b} f(x)\,dx = F(b) - F(a)`
  - [ ] Sector Area: `A = \frac{1}{2} r^2 \theta`
  - [ ] Cylinder Volume: `V = \pi r^2 h`
  - [ ] Wave Speed: `v = f \lambda`
  - [ ] Period: `T = \frac{1}{f}`
  - [ ] Equilibrium: `K_c = \frac{[C]^c [D]^d}{[A]^a [B]^b}`

#### 3. Manim Scene Spec (ISS-100)
- Sections with renderer="manim" must have:
  - [ ] visual_beats array
  - [ ] manim_scene_spec with objects and animation_sequence

#### 4. Renderer Selection
- Biology → renderer="video"
- Math/Geometry/Physics/Chemistry with formulas → renderer="manim"
- Intro/Summary → renderer="remotion"

#### 5. No Fabricated Quiz (ISS-097)
- Since source has no quiz, output should have no quiz section

#### 6. Recap Scenes (ISS-092)
- Recap section must have 5 scenes
- Each scene must have video_prompt (50-80 words for Video Renderer to expand)

## Test Command

```bash
python scripts/test_v14_pipeline.py \
  --mode full_test \
  --markdown-file /tmp/test_sample.md \
  --tts-provider estimate \
  --skip-wan \
  --report /tmp/v14_test_report.json
```

## Analysis Script

After test completion, analyze presentation.json:

```bash
# Extract section types and titles
grep -E '"section_type"|"title"' player/jobs/<job_id>/presentation.json | head -30

# Check for LaTeX formulas
grep -o '"formula":.*' player/jobs/<job_id>/presentation.json

# Check for manim_scene_spec
grep -c 'manim_scene_spec' player/jobs/<job_id>/presentation.json

# Count content sections
grep -c '"section_type": "content"' player/jobs/<job_id>/presentation.json
```

## Issue Logging
Any failure must be logged to issues.json with:
- Issue ID (ISS-XXX)
- Title
- Root cause
- Fix applied
- Files modified

## Iteration
Repeat test until all validations pass.
