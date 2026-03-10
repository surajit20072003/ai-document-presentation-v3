# Project: AI Animated Education - Phase 1

## Core Goal

Build a production-grade AI pipeline that converts PDF chapters into topic-wise explanation videos (MP4), synchronized with narration, and presented in a YouTube/Vimeo-style HTML player.

## Non-Negotiable Principles

1. The LLM is the DIRECTOR and BRAIN
2. The LLM decides:
   - Topic breakdown
   - Narration
   - Subtitle timing
   - Explanation strategy
   - Renderer choice (WAN vs Manim)
   - Layout (content vs avatar zones)
   - Video role (primary explanation visual)
3. The frontend is a DUMB EXECUTOR
4. One MP4 per topic (best pedagogy)
5. All decisions must be traceable via JSON logs

## Renderers

### Manim (Local CLI)
Used for:
- Mathematics
- Geometry
- Graphs
- Formula derivations

### WAN (via kie.ai API)
Used for:
- Biology processes
- Physics concepts
- Chemistry reactions
- Conceptual visual explanations

## Current Status

- [x] Project structure scaffolded
- [x] LLM client with OpenRouter integration
- [x] PDF to Markdown conversion (stub + API ready)
- [x] WAN video renderer client
- [x] Manim animation renderer
- [x] TTS audio generation
- [x] Main pipeline orchestrator
- [x] Flask API endpoints
- [x] YouTube-style HTML5 player
- [x] Generation trace logging

## Phase 2 Roadmap

- [ ] Real AI avatar video generation
- [ ] Gesture synchronization system
- [ ] Interactive dev mode (drag/resize)
- [ ] Real PDF parsing integration
- [ ] Job queue for background processing
- [ ] Video caching layer
