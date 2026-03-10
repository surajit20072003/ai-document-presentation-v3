# 📋 V3.0 Requirements & Build Specification
**Status**: Approved for Development  
**Supersedes**: V2.5 Director Bible  
**Last Updated**: 2026-03-08  
**Change Log**: Added gesture controls (pinch-zoom confirmed), player visual direction confirmed from Trig player (80% baseline). 2026-03-08: Full interactivity system defined — taxonomy, params contract, Director rules, code generator patterns, validator rules, JSON schema. 2026-03-08 (v2): Understanding quiz made mandatory for every partition. Image source handling system added — three modes (video reference, texture, interactive hotspot).

---

## ✅ Deliverables Status (Updated 2026-03-08)

| File | Purpose | Status |
|---|---|---|
| `requirements_build_for_v3.md` | This document — full spec | ✅ Updated 2026-03-08 |
| `trig_v3_player.html` | V3 player with gesture controls + avatar master clock | ✅ Built |
| `topic_reference_scene.js` | Reference Three.js scene — the API contract for threejs_code_generator | ✅ Built |
| `threejs_system_prompt_v2.txt` | Hardened code generator system prompt (closure fix + interactivity) | ✅ Built 2026-03-08 |
| `fill_prompt_v2.py` | Prompt builder — fills per-beat user prompt from presentation.json | ✅ Built 2026-03-08 |
| `director_v3_partition_prompt.txt` | Updated LLM prompt with threejs_spec schema + interactivity rules | Phase B |
| `threejs_code_generator.py` | LLM executor that writes .js scene files | Phase B |

**What a developer or AI agent gets from these files:**
- The WHY, rules, schema, hard constraints → `requirements_build_for_v3.md`
- The visual baseline, working gesture controls, avatar clock → `trig_v3_player.html`
- The exact API contract every Three.js scene must implement → `topic_reference_scene.js`
- The hardened system prompt for Claude Sonnet code generation → `threejs_system_prompt_v2.txt`
- The per-beat prompt builder that feeds real data into the LLM → `fill_prompt_v2.py`

---

## 🎯 V3 Core Philosophy

> **V2.5** = Text-heavy teaching, visuals as support  
> **V3** = Visual-first. Students understand better when they **see** — not read.  
> The LLM reads source (text + images), converts everything into live interactive Three.js scenes or WAN/LTX2 video. Text is eliminated from Content sections entirely.

**The goal**: A student watching a V3 lesson should feel like they have a private tutor drawing on a board and demonstrating live — not reading a textbook on screen.

**Non-Negotiable Sync Rule**: The LLM is responsible for sync. The Director co-authors narration duration and Three.js animation duration in the same call. They always match. The player does not perform sync logic.

**Avatar `.mp4` is the master clock — everything is written to match it.**

**Fallback Only** (should never occur): If Three.js finishes before avatar → freeze on last frame until avatar ends. Never loop. Never clear.

---

## 📦 What Changes vs V2.5

### ✅ Keep Exactly As-Is (70%)
- Source Processing / Smart Chunker (Phase 0)
- ThreadPoolExecutor parallel engine
- TTS + Avatar generation core
- WAN / LTX2 rendering pipeline
- Pointer integrity / anti-hallucination rules
- Memory flashcards (5 cards, flip interaction)
- Recap cinematic (5 segments, WAN video)
- Intro section (avatar-only)
- Summary section (bullet list)
- `presentation.json` stitching logic (extended, not replaced)
- `v25_validator.py` structure (rules updated for V3)
- Indian cultural analogies in narration

### 🔄 Modify (20%)
- `director_partition_prompt.txt` → V3 schema with `threejs_spec`
- `renderer_executor.py` → add Three.js generator branch
- `avatar_generator.py` → add `mode: quiz` for 3 clips per question
- `presentation.json` schema → new fields, same structure
- Player frontend → full V3 rebuild

### ❌ Deprecate (10%)
- `manim_code_generator.py` → replaced by `threejs_code_generator.py`
- `text_layer: SHOW` in Content/Example sections → eliminated
- Static text slides in teaching sections → replaced by Three.js scenes

---

## 🏗️ V3 Pipeline (Phase by Phase)

```
Phase 0: Smart Chunker              — unchanged
         + Image Detector (NEW)     — flags images in source for Director
Phase 1: Directors (Parallel Threads)
         Global Director            — UNCHANGED (Intro/Summary/Memory/Recap)
         Partition Director V3      — NEW schema (threejs_spec, understanding_quiz)

Phase 2: Three.js Generation (blocking, like Manim was)
         → Claude Sonnet reads threejs_spec → writes topic_{id}_beat_{idx}.js

         Avatar Generator (MODIFIED)
         → Content: 1 clip per segment as before
         → Quiz: 3 clips per question
             avatar_quiz_{id}_q{n}_question.mp4
             avatar_quiz_{id}_q{n}_correct.mp4
             avatar_quiz_{id}_q{n}_wrong.mp4

Phase 3: WAN / LTX2 Rendering      — UNCHANGED

Phase 4: Stitch presentation.json  — UNCHANGED + new fields

Phase 5: Player V3                 — FULL REBUILD
```

---

## 📝 Deliverable 1: `director_v3_partition_prompt.txt`

### New Fields (V3 additions to existing schema)

**Added:**
- `threejs_spec` — 100+ word scene description (replaces `manim_spec`)
- `segment_duration_seconds` — Director sets this, LLM animation fills it
- `understanding_quiz` — mandatory per partition (see Quiz section)
- `renderer: "threejs"` — new valid renderer value
- `image_source` — base64 or path of source image passed to Director when detected
- `image_mode` — how the Director chose to use the image (see Image Handling below)

### Renderer Decision Tree

```
STEP 1 — Subject-based decision:
    Math / Physics / Chemistry / Optics / Logic → renderer: "threejs"
    Biology / History / Geography / General     → renderer: "video"

STEP 2 — Source image present (overrides STEP 1 for that beat):
    → Director analyses image content → picks image_mode (see below)
    → renderer is always "threejs" when image_mode is set
```

---

## 🖼️ Image Source Handling (V3)

When the source document contains an image, the Smart Chunker flags it and passes it to the Partition Director. The Director analyses the image and picks one of three modes.

### Three Image Modes

| Mode | When to use | What gets generated |
|---|---|---|
| `video_reference` | Photo, illustration, real-world scene — best shown as cinematic video | Image passed as reference frame to WAN/LTX2. Video renderer used. |
| `texture` | Diagram, chart, graph, table — information-dense, needs to stay readable | Image rendered as Three.js texture on a plane. Animated labels/arrows drawn on top. |
| `interactive_hotspot` | Labelled diagram — parts that need individual explanation (anatomy, circuit, triangle) | Image as texture + invisible clickable/hoverable regions drawn over key parts. |

### Director Decision Rules

```
Is the image a photograph or realistic illustration?
  YES → video_reference

Is the image a diagram/chart with labelled parts?
  YES, parts need individual explanation → interactive_hotspot
  YES, parts don't need clicking         → texture

Is the image a simple graph or data table?
  → texture
```

### `image_mode` in `segment_spec`

```json
{
  "segment_id": "seg_2",
  "renderer": "threejs",
  "threejs_spec": "The source diagram shows a right-angled triangle ABC. Render it as a texture on a dark plane. At 2s animate a gold arrow pointing to the hypotenuse AC with a label. At 5s animate a rose arrow pointing to BC with label 'Opposite'.",
  "segment_duration_seconds": 10.0,
  "threejs_file": "threejs/topic_3_beat_1.js",
  "image_mode": "texture",
  "image_source": "jobs/abc123/images/triangle_diagram.jpg",
  "interaction": {
    "type": "hover_highlight",
    "target": "diagram_regions",
    "description": "Student hovers over each side — it highlights and shows its name",
    "timeout_seconds": 10
  }
}
```

For `video_reference` mode, `renderer` is `"video"` and `image_source` is passed to the WAN generator as a reference frame — no `threejs_file` generated.

### Code Generator: Texture Mode Pattern

When `image_mode` is `"texture"` or `"interactive_hotspot"`, the code generator loads the image as a Three.js texture:

```javascript
// In initScene setup — load source image as texture on a plane
var loader  = new THREE.TextureLoader();
var imgTex  = loader.load(params.imageSrc || '');   // player passes imageSrc via params
var imgMat  = new THREE.MeshBasicMaterial({ map: imgTex, transparent: true });
var imgGeo  = new THREE.PlaneGeometry(8.0, 5.0);    // fill safe zone
var imgMesh = new THREE.Mesh(imgGeo, imgMat);
imgMesh.position.set(0, 0, 0);
scene.add(imgMesh);

// Then animate labels/arrows on top as normal
// For interactive_hotspot: define invisible raycaster hit boxes over key regions
```

### `params` extension for image mode

The player passes `imageSrc` in `params` when `image_mode` is set:

```javascript
var params = {
  getTime:    function() { return avatarVideo.currentTime; },
  onInteract: function(type, data) { /* ... */ },
  imageSrc:   beat.image_source || null   // NEW — path to source image
};
```

### Validator Rules for Image Mode

```
image_mode present → image_source must also be present (hard fail if missing)
image_mode: video_reference → renderer must be "video", no threejs_file (hard fail if threejs)
image_mode: texture / interactive_hotspot → renderer must be "threejs" (hard fail if video)
interactive_hotspot → interaction field must be non-null (hard fail if null)
```

### `threejs_spec` Field Rules

100+ words. Must include all 8 items in order:

1. **Scene description** — what objects are shown and their initial state
2. **Animation sequence** — what happens in order with second-level timing
3. **Interactivity** — which interaction type (see taxonomy below), what object, what it changes. Write `none` if not interactive.
4. **Camera** — position, angle, movement if any
5. **Colours** — background (#0d1117 default), objects, labels
6. **Labels** — described as plain text (not LaTeX syntax)
7. **Duration** — exact seconds matching `segment_duration_seconds`
8. **Complexity** — `simple | medium | complex`

---

## 🖱️ Scene Interactivity System (V3)

### Interaction Taxonomy

Five interaction types are supported. The Director chooses at most one per beat.

| Type | What the Student Does | Best For | Complexity Required |
|---|---|---|---|
| `hover_highlight` | Mouse over an object — it glows and a tooltip appears | Discovery, labelling, anatomy of a diagram | simple or above |
| `click_reveal` | Click a highlighted object — a label or formula appears | Step-by-step reveals, hidden answers | simple or above |
| `drag_point` | Drag a vertex or point — geometry updates live | Triangles, vectors, force diagrams, graphs | medium or above |
| `rotate_inspect` | Drag anywhere — a 3D object rotates freely | 3D geometry, molecules, prisms, solids | medium or above |
| `slider` | Drag a control handle along a track — a value changes (angle, speed, wavelength) | Trigonometry ratios, physics waves, optics | complex only |

### Director Rules — When to Specify Interactivity

```
complexity: simple   → hover_highlight or click_reveal only. No drag. No slider.
complexity: medium   → hover_highlight, click_reveal, drag_point, or rotate_inspect.
complexity: complex  → any single type, plus hover_highlight as secondary.

NEVER use interactivity if:
  - segment_duration_seconds < 8.0  (not enough time for student to discover and act)
  - beat is the first beat of a section (student is still orienting)
  - more than one primary interaction type would be needed

NEVER combine drag_point + rotate_inspect in the same beat.
NEVER combine slider + drag_point in the same beat.
hover_highlight may always be added as a passive secondary layer.
```

### What to Write in `threejs_spec` for Each Type

**hover_highlight:**
> "Each side of the triangle is a hoverable object. When the student hovers over a side, it brightens to white and a gold label appears above it naming the side. Hover leaves no permanent change — label fades when mouse moves away."

**click_reveal:**
> "The hypotenuse line is drawn in dim grey initially. A subtle pulse animation indicates it is clickable. When the student clicks it, the line brightens to gold and the label 'Hypotenuse' fades in above it. The click is one-way — no un-click."

**drag_point:**
> "Vertex C is draggable (rendered as a rose-coloured circle handle). As the student drags C vertically, the opposite side BC redraws in real time and the label showing its length updates. The angle arc at A also redraws to match. Dragging is clamped: C stays within Y[0.5, 3.0] and X[2.0, 2.5]."

**rotate_inspect:**
> "A 3D triangular prism sits at the origin. The student can drag anywhere on the canvas to rotate it freely on the Y and X axes. A dim label 'Drag to rotate' fades out after 3s. Rotation inertia: 0.92 damping factor."

**slider:**
> "A horizontal slider track sits at Y=-2.5, X[-3, 3]. A gold handle sits at X=0 (theta=45°). As the student drags the handle, the triangle above redraws with the new angle, and the sin/cos value labels update in real time. Range: 5° to 85°."

---

### `interaction` Field in `presentation.json` (NEW)

The Director must emit an `interaction` object alongside `threejs_spec` in every `segment_spec`. If no interactivity, emit `"interaction": null`.

```json
"segment_specs": [
  {
    "segment_id": "seg_1",
    "renderer": "threejs",
    "threejs_spec": "...",
    "segment_duration_seconds": 12.0,
    "threejs_file": "threejs/topic_3_beat_0.js",
    "interaction": null
  },
  {
    "segment_id": "seg_3",
    "renderer": "threejs",
    "threejs_spec": "...",
    "segment_duration_seconds": 15.0,
    "threejs_file": "threejs/topic_3_beat_2.js",
    "interaction": {
      "type": "drag_point",
      "target": "vertex_C",
      "description": "Student drags vertex C — triangle redraws live",
      "timeout_seconds": 10
    }
  }
]
```

`timeout_seconds` — if the student does not interact within this many seconds, the player auto-advances. Always set to 10 unless Director has a specific reason for more time.

---

### `params` Contract — Full Definition (V3)

The player passes `params` into `initScene()`. This is the complete contract:

```javascript
// What the PLAYER provides to the scene:
var params = {

  // Master clock — always present
  getTime: function() { return avatarVideo.currentTime; },

  // Interaction callback — always present, scene calls it when student acts
  // type: 'hover' | 'click' | 'drag' | 'rotate' | 'slide'
  // data: { target, value } — scene-specific payload
  onInteract: function(type, data) { /* player logs, shows hints, etc. */ },

};

// What the SCENE returns — all 3 original hooks PLUS 3 optional interaction hooks:
return {
  onResize:      onResize,      // required — player calls on window resize
  onPinchZoom:   onPinchZoom,   // required — player calls on pinch gesture
  dispose:       dispose,       // required — player calls before next scene

  // Optional — only defined if the scene is interactive.
  // Player checks: if (scene.onPointerMove) scene.onPointerMove(nx, ny, isDrag)
  onPointerMove: onPointerMove, // nx, ny = normalised [0,1] coords; isDrag = bool
  onPointerDown: onPointerDown, // nx, ny = normalised coords at mousedown/touchstart
  onPointerUp:   onPointerUp,   // nx, ny = normalised coords at mouseup/touchend
};
```

**Player-side wiring** (what the player must do for every interactive beat):

```javascript
var scene = initScene(container, beat.segment_duration_seconds, params);

// Wire pointer events if the scene declared them
if (scene.onPointerMove || scene.onPointerDown) {
  container.addEventListener('mousemove', function(e) {
    var r = container.getBoundingClientRect();
    var nx = (e.clientX - r.left) / r.width;
    var ny = (e.clientY - r.top)  / r.height;
    if (scene.onPointerMove) scene.onPointerMove(nx, ny, mouseIsDown);
  });
  container.addEventListener('mousedown', function(e) {
    mouseIsDown = true;
    var r = container.getBoundingClientRect();
    if (scene.onPointerDown)
      scene.onPointerDown((e.clientX - r.left)/r.width, (e.clientY - r.top)/r.height);
  });
  container.addEventListener('mouseup', function(e) {
    mouseIsDown = false;
    var r = container.getBoundingClientRect();
    if (scene.onPointerUp)
      scene.onPointerUp((e.clientX - r.left)/r.width, (e.clientY - r.top)/r.height);
  });
  // Touch equivalents follow the same pattern with e.touches[0]
}

// Interaction timeout — auto-advance if student doesn't interact
if (beat.interaction && beat.interaction.timeout_seconds) {
  interactionTimer = setTimeout(function() {
    advanceToNextScene();
  }, beat.interaction.timeout_seconds * 1000);
}
// Clear timer on params.onInteract call
```

### Code Generator Patterns for Each Interaction Type

These are the implementation patterns Claude Sonnet must use in generated `.js` files.

**hover_highlight pattern:**
```javascript
// In setup — build a raycaster and track hovered object
var raycaster = new THREE.Raycaster();
var mouse     = new THREE.Vector2();
var hovered   = null;

function onPointerMove(nx, ny, isDrag) {
  mouse.x =  (nx * 2) - 1;
  mouse.y = -(ny * 2) + 1;
  raycaster.setFromCamera(mouse, camera);
  var hits = raycaster.intersectObjects(hoverTargets);
  var hit  = hits.length ? hits[0].object : null;
  if (hit !== hovered) {
    if (hovered) { hovered.material.color.setHex(hovered.userData.baseColor); }
    hovered = hit;
    if (hovered) {
      hovered.material.color.setHex(0xffffff);   // brighten
      tooltipLabel.visible = true;
      tooltipLabel.position.copy(hovered.position).y += 0.6;
      if (params && params.onInteract) params.onInteract('hover', { target: hovered.userData.name });
    } else {
      tooltipLabel.visible = false;
    }
  }
}
```

**click_reveal pattern:**
```javascript
var revealed = {};

function onPointerDown(nx, ny) {
  mouse.x =  (nx * 2) - 1;
  mouse.y = -(ny * 2) + 1;
  raycaster.setFromCamera(mouse, camera);
  var hits = raycaster.intersectObjects(clickTargets);
  if (!hits.length) return;
  var obj = hits[0].object;
  if (revealed[obj.uuid]) return;
  revealed[obj.uuid] = true;
  obj.material.color.setHex(CLR.gold);
  obj.userData.revealLabel.visible = true;
  if (params && params.onInteract) params.onInteract('click', { target: obj.userData.name });
}
```

**drag_point pattern:**
```javascript
var dragging = null;
var dragPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
var dragPoint = new THREE.Vector3();

function onPointerDown(nx, ny) {
  mouse.x = (nx * 2) - 1; mouse.y = -(ny * 2) + 1;
  raycaster.setFromCamera(mouse, camera);
  var hits = raycaster.intersectObjects(dragHandles);
  if (hits.length) dragging = hits[0].object;
}
function onPointerMove(nx, ny, isDrag) {
  if (!dragging) return;
  mouse.x = (nx * 2) - 1; mouse.y = -(ny * 2) + 1;
  raycaster.setFromCamera(mouse, camera);
  raycaster.ray.intersectPlane(dragPlane, dragPoint);
  // clamp to safe zone
  dragging.position.x = Math.max(-5, Math.min(5, dragPoint.x));
  dragging.position.y = Math.max(-3, Math.min(3, dragPoint.y));
  rebuildGeometry();   // scene-specific: redraw lines, update labels
  if (params && params.onInteract) params.onInteract('drag', { x: dragging.position.x, y: dragging.position.y });
}
function onPointerUp(nx, ny) { dragging = null; }
```

**rotate_inspect pattern:**
```javascript
var lastMouse = null;
var targetGroup = null;  // the object to rotate

function onPointerDown(nx, ny) { lastMouse = { x: nx, y: ny }; }
function onPointerMove(nx, ny, isDrag) {
  if (!isDrag || !lastMouse) return;
  var dx = (nx - lastMouse.x) * Math.PI * 2;
  var dy = (ny - lastMouse.y) * Math.PI * 2;
  targetGroup.rotation.y += dx;
  targetGroup.rotation.x += dy;
  lastMouse = { x: nx, y: ny };
  if (params && params.onInteract) params.onInteract('rotate', {});
}
function onPointerUp() { lastMouse = null; }
```

**slider pattern:**
```javascript
var sliderValue  = 0.5;   // 0.0 to 1.0
var sliderActive = false;
var SLIDER_X_MIN = -2.5, SLIDER_X_MAX = 2.5;

function onPointerDown(nx, ny) {
  mouse.x = (nx * 2) - 1; mouse.y = -(ny * 2) + 1;
  raycaster.setFromCamera(mouse, camera);
  var hits = raycaster.intersectObjects([sliderHandle]);
  if (hits.length) sliderActive = true;
}
function onPointerMove(nx, ny, isDrag) {
  if (!sliderActive) return;
  // map nx to world x
  var worldX = (nx - 0.5) * (camera.position.z) * camera.aspect * 1.4;
  sliderValue = Math.max(0, Math.min(1,
    (worldX - SLIDER_X_MIN) / (SLIDER_X_MAX - SLIDER_X_MIN)));
  sliderHandle.position.x = SLIDER_X_MIN + sliderValue * (SLIDER_X_MAX - SLIDER_X_MIN);
  updateSceneForSliderValue(sliderValue);   // scene-specific
  if (params && params.onInteract) params.onInteract('slide', { value: sliderValue });
}
function onPointerUp() { sliderActive = false; }
```

### Two Quiz Sets Per Lesson

A V3 lesson may contain **two independent quiz sets**. They are always separate sections:

| Quiz Set | Origin | Count | Position in lesson | Generator |
|---|---|---|---|---|
| **Understanding Quiz** | LLM Director — generated from content | Exactly 1 per content partition — **mandatory** | Immediately after its content section | Partition Director |
| **Document Quiz** | Extracted from source document if MCQs exist | 0 or N questions — only if source contains them | Before the Memory section | Global Director |

Both use identical question schema and 3-clip avatar contract below.  
`quiz_origin` field distinguishes them: `"understanding"` vs `"document"`.

**Understanding Quiz rules:**
- Always generated. No skip condition. Even image-heavy partitions get one.
- Director writes 1 question testing the core concept of that partition.
- 4 options (A/B/C/D), 1 correct, explanation in `wrong_script`.

**Document Quiz rules:**
- Only present if source document contains MCQ-style questions.
- Global Director extracts them verbatim (anti-hallucination pointer rule applies).
- May have multiple questions grouped in one section.

### Quiz Schema V3

```json
{
  "section_type": "quiz",
  "quiz_origin": "document | understanding",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "...",
      "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
      "correct_option": "B",
      "avatar_clips": {
        "question": "avatars/en/quiz_1_q1_question.mp4",
        "correct":  "avatars/en/quiz_1_q1_correct.mp4",
        "wrong":    "avatars/en/quiz_1_q1_wrong.mp4"
      },
      "narration": {
        "question_script": "...",
        "correct_script":  "...",
        "wrong_script":    "..."
      }
    }
  ]
}
```

---

## 📝 Deliverable 2: `threejs_code_generator.py`

> **Reference implementation**: See `topic_reference_scene.js` — this is the exact output format the generator must produce. Every generated `.js` file must implement `initScene(container, totalDuration, params)` and return `{ onResize, onPinchZoom, dispose }` plus optional pointer hooks.

Mirrors `manim_code_generator.py` in structure. Replaces Python output with JS.

### Hardened System Prompt Rules for Claude Sonnet

1. **CDN only** — Three.js r128 from cdnjs — no npm, no bundler, no imports
2. **Self-contained** — single `.js` file
3. **Duration contract** — `totalDuration` seconds injected; use `getElapsed()` not `clock.getElapsedTime()` directly
4. **Entry point** — `initScene(container, totalDuration, params)` — exact signature
5. **Safe zone** — objects within X[-6, 6], Y[-3.5, 3.5], Z[-5, 5]
6. **Text labels** — canvas texture on PlaneGeometry only — no FontLoader, no troika
7. **Freeze rule** — hold last frame on completion. Never loop. Never clear.
8. **Silent fail** — no `alert()`, no `console.error()`, no thrown errors
9. **Closure pattern** — `fadeIn()` and `animateDraw()` closures created BEFORE `animate()`, never called inside it
10. **No scene.add() inside animate()** — all objects added at setup time, opacity starts at 0
11. **Interactivity** — if `interaction` field is non-null, implement the matching pattern from this spec. Always return `onPointerMove`, `onPointerDown`, `onPointerUp` hooks in the return object (even if no-ops when non-interactive).
12. **CLR not C** — colour palette named `CLR` — single letter `C` reserved for triangle vertices

### Output Naming
```
jobs/{job_id}/threejs/topic_{partition_id}_beat_{segment_idx}.js
```

---

## 📝 Deliverable 3: `player_v3.html`

> **Built**: See `trig_v3_player.html` — Trigonometry lesson player with all Phase A features implemented.
> Gesture controls (HandPose), avatar master clock, pinch-zoom, touch controls, mobile responsive.

### Layer Stack

```
┌─────────────────────────────────────────────────┐
│  Layer 4: UI Overlay                            │
│  — Quiz A/B/C/D buttons                         │
│  — Gesture indicator (top-left, semi-transparent)│
│  — Pinch-zoom indicator                         │
│  — Interaction hint (e.g. "Drag the point ↑")   │
│  — Progress + section dots (bottom)             │
│  — Section title (top, fades after 2s)          │
├─────────────────────────────────────────────────┤
│  Layer 3: Avatar <video>   ← MASTER CLOCK       │
│  — Bottom-right (desktop) / bottom-center (mobile)│
│  — Always visible, weatherman mode              │
│  — avatar.onended → advance scene               │
│    (suppressed during active interaction)        │
├─────────────────────────────────────────────────┤
│  Layer 2: Three.js <div>                        │
│  — Shown when renderer == "threejs"             │
│  — initScene(container, duration, params)       │
│  — Freeze last frame if avatar still running    │
│  — Pinch zoom applied to camera here            │
│  — Pointer events forwarded if scene declares   │
│    onPointerMove / onPointerDown / onPointerUp  │
├─────────────────────────────────────────────────┤
│  Layer 1: WAN/LTX2 <video>                     │
│  — Shown when renderer == "video"               │
│  — Hidden when renderer == "threejs"            │
└─────────────────────────────────────────────────┘
```

### Master Clock

```javascript
// Avatar ends → advance (unless student is mid-interaction)
avatarVideo.addEventListener('ended', function() {
  if (!interactionActive) advanceToNextScene();
});

// No sync logic in player. LLM guarantees duration match.
var scene = initScene(container, beat.segment_duration_seconds, params);

// Wire pointer events if scene declared interaction hooks
if (scene.onPointerDown || scene.onPointerMove) {
  wirePointerEvents(container, scene);
}

// Interaction timeout — auto-advance if student doesn't interact
if (beat.interaction && beat.interaction.timeout_seconds) {
  interactionTimer = setTimeout(advanceToNextScene,
                                beat.interaction.timeout_seconds * 1000);
}
```

### Quiz Flow (Pre-Baked Branching)

```
1. Play quiz_{id}_q{n}_question.mp4 (avatar reads question)
2. A/B/C/D buttons appear after 1s
3. Avatar clip ends → pause. Buttons remain.
4. Student clicks answer (or gesture selects)
5. IF correct → play _correct.mp4 → button glows green
   IF wrong   → play _wrong.mp4   → correct=green, wrong=red
6. Clip ends → advance to next question or next section
```

---

## 🤚 Gesture Controls Specification (CONFIRMED 2026-03-05)

### Engine
- **Library**: TensorFlow.js HandPose (CDN, loaded async)
- **Camera**: `MediaDevices.getUserMedia` — front-facing
- **Fallback**: Camera denied or HandPose unavailable → silent disable. Touch/click takes over. No error shown.

### Gesture Map (FULLY CONFIRMED)

| Gesture | Action |
|---|---|
| ✋ Open palm (held 0.5s) | **Pause / Resume** |
| 👇 Point down | **Replay current scene** |
| 👋 Wave side to side (2+ cycles) | **Next scene** |
| 🤏 Pinch (thumb + index, then move apart/together) | **Zoom in/out on Three.js scene** |
| ☝️ Point up | Reserved |

### Pinch Zoom Implementation

```javascript
// Applies to Three.js camera only. WAN video and quiz do not zoom.
if (gesture === 'pinch') {
  const pinchDist = getPinchDistance(landmarks);
  const delta = (pinchDist - lastPinchDist) * ZOOM_SENSITIVITY;
  camera.position.z = clamp(camera.position.z - delta, MIN_ZOOM=2.0, MAX_ZOOM=15.0);
  lastPinchDist = pinchDist;
}
```

### Gesture Indicator UI
- Semi-transparent hand icon, top-left corner
- Shows gesture name for 1.5s when detected: gold = active, dim = idle
- Hidden on mobile (touch mode active instead)

### Mobile Touch Controls

| Touch | Action |
|---|---|
| Single tap | Pause / Resume |
| Swipe left | Next scene |
| Swipe right | Replay |
| Double tap | Toggle controls |
| Pinch gesture | Zoom in/out on Three.js |

---

## 🎨 Player Visual Direction (CONFIRMED 2026-03-05)

**The Trigonometry player built in this session is the 80% visual baseline for V3.**

It establishes:
- Dark background `#0d1117` — the canvas for all content
- **Chalk stroke-by-stroke drawing** for triangles, diagrams, geometry
- Colour system: gold (key terms), teal (adjacent), rose (opposite/highlight), sky blue (labels), lavender (proofs), green (answers/correct)
- **Caveat cursive** for chalk labels and headings
- **JetBrains Mono** for equations
- Content appears segment-by-segment — timed reveals, not all at once
- 3D flip flashcards for Memory section
- Cinematic staggered segments for Recap

**The 20% still to build on top of this baseline:**
1. Three.js integration replaces chalk canvas for complex STEM scenes
2. Gesture control layer (HandPose + pinch zoom)
3. Avatar master clock drives scene advance (not manual arrow buttons)
4. Fully data-driven from `presentation.json` at runtime — zero hardcoded content
5. True mobile responsive layout

---

## 🗂️ Updated `presentation.json` Schema (V3 Extensions)

New fields only — all V2.5 fields unchanged:

```json
{
  "version": "3.0",
  "sections": [
    {
      "section_type": "content",
      "renderer": "threejs",
      "segments": [{
        "segment_id": "seg_1",
        "segment_duration_seconds": 15.0,
        "threejs_file": "jobs/abc123/threejs/topic_1_beat_1.js",
        "interaction": null,
        "display_directives": {
          "text_layer": "hide",
          "visual_layer": "show",
          "visual_type": "threejs",
          "avatar_layer": "show"
        }
      }]
    },
    {
      "section_type": "content",
      "renderer": "threejs",
      "segments": [{
        "segment_id": "seg_3",
        "segment_duration_seconds": 15.0,
        "threejs_file": "jobs/abc123/threejs/topic_1_beat_3.js",
        "interaction": {
          "type": "drag_point",
          "target": "vertex_C",
          "description": "Student drags vertex C — triangle redraws live",
          "timeout_seconds": 10
        },
        "display_directives": {
          "text_layer": "hide",
          "visual_layer": "show",
          "visual_type": "threejs",
          "avatar_layer": "show"
        }
      }]
    },
    {
      "section_type": "quiz",
      "quiz_origin": "understanding",
      "questions": [{
        "question_id": "q1",
        "avatar_clips": {
          "question": "avatars/en/quiz_1_q1_question.mp4",
          "correct":  "avatars/en/quiz_1_q1_correct.mp4",
          "wrong":    "avatars/en/quiz_1_q1_wrong.mp4"
        }
      }]
    }
  ]
}
```

### `interaction` Field Values

| Field | Type | Description |
|---|---|---|
| `type` | string | One of: `hover_highlight`, `click_reveal`, `drag_point`, `rotate_inspect`, `slider` |
| `target` | string | Human-readable name of the interactive object (for logging/hints) |
| `description` | string | One sentence — what the student does and what changes |
| `timeout_seconds` | int | Auto-advance if no interaction within N seconds. Always 10 unless Director specifies otherwise. |

---

## ✅ V3 Validator Rules

| Rule | V2.5 | V3 |
|---|---|---|
| Content `text_layer` | Mixed | Always `hide` — hard fail if `show` |
| Renderer values | `manim`, `video`, `none` | `threejs`, `video`, `none` |
| `threejs_file` exists | N/A | Hard fail if missing for `renderer: threejs` |
| Quiz avatar clips | 1 per question | 3 per question — hard fail if any missing |
| `segment_duration_seconds` | N/A | Required on all content segments |
| Understanding quiz | N/A | **Mandatory** on every content partition — hard fail if missing |
| Sync guarantee | Manim duration | LLM-authored = avatar duration — validated at stitch |
| `interaction` field | N/A | Must be present on every segment_spec — `null` or valid object |
| `interaction.type` | N/A | Must be one of the 5 defined types — hard fail on unknown value |
| Interactivity + duration | N/A | Hard fail if `interaction` non-null and `segment_duration_seconds` < 8.0 |
| Interactivity + complexity | N/A | Hard fail if `slider` used with `complexity: simple` or `medium` |
| `image_mode` present | N/A | `image_source` must also be present — hard fail if missing |
| `image_mode: video_reference` | N/A | `renderer` must be `"video"`, no `threejs_file` — hard fail if threejs |
| `image_mode: texture / interactive_hotspot` | N/A | `renderer` must be `"threejs"` — hard fail if video |
| `interactive_hotspot` | N/A | `interaction` must be non-null — hard fail if null |

---

## 🚫 Hard Rules (Non-Negotiable)

1. **LLM owns sync** — Director writes narration and Three.js duration together. Player never adjusts timing.
2. **Avatar is master clock** — `avatar.onended` is the only scene advance trigger (suppressed during active interaction).
3. **No text in content** — `text_layer: hide` always in Content/Example sections.
4. **Three.js freeze on error** — Only fallback. Never happens in production.
5. **3 avatar clips per quiz question** — question, correct, wrong. Always.
6. **Understanding quiz is mandatory** — Every content partition generates exactly 1 understanding quiz. No skip condition. Director always writes it.
7. **All prompts 100+ words** — `threejs_spec`, `video_prompt`, recap prompts.
8. **Gesture fallback is silent** — Camera denied = touch/click mode. No errors.
9. **Pinch zoom on Three.js only** — WAN video and quiz overlay do not zoom.
10. **Interactivity is opt-in** — Every beat has `interaction` field. `null` is the default. Never invent interaction where the spec says none.
11. **One interaction type per beat** — Never combine drag_point + rotate_inspect, or slider + drag_point in the same beat. hover_highlight may always be added as a passive secondary.
12. **Timeout is mandatory** — Every interactive beat has `timeout_seconds`. Player must auto-advance when it fires.
13. **Interaction does not extend duration** — `segment_duration_seconds` is fixed. The student interacts within that window. The timeout is a safety net, not a wait loop.

---

## 📅 Build Order (Phased)

```
PHASE A — Make the player production-ready ✅ COMPLETE
  A1: Trig player visual baseline (80% approved by product owner)        ✅
  A2: Avatar master clock — avatar.onended drives all scene advance      ✅
  A3: Gesture controls — HandPose + pinch zoom + wave + point            ✅
  A4: Mobile responsive — touch controls (swipe/pinch/tap)               ✅
  A5: Reference Three.js scene — API contract documented                 ✅

PHASE B — Three.js pipeline + interactivity ✅ COMPLETE
  B1: threejs_code_generator.py                                          ✅
  B2: director_v3_partition_prompt.txt (schema + interactivity taxonomy) ✅
  B3: Player pointer-event wiring (onPointerDown/Move/Up → scene hooks)  ✅
  B4: Player interaction timeout (auto-advance after timeout_seconds)    ✅
  B5: Interaction hint UI ("Drag the point ↑" fades in at beat start)   ✅

PHASE C — Quiz, Image Handling, Validation, Polish ← CURRENT
  C1: Pre-baked quiz branching (3 avatar clips per question) E2E verify
  C2: Understanding quiz — remove skip condition, make mandatory in Director prompt
  C3: Two-quiz architecture — document quiz (Global) + understanding quiz (Partition)
  C4: Image source handling — Smart Chunker image flag → Director image_mode decision
  C5: Texture / interactive_hotspot mode in threejs_code_generator
  C6: params.imageSrc wiring in player
  C7: v3_validator.py — image_mode rules + mandatory understanding quiz rule
  C8: v3.0_Director_Bible.md published
```
