# AI Document Presentation - V2.5 Director Pipeline

Transform educational documents into rich, animated video presentations with AI Avatar narration, Manim animations, and synchronized visual content.

## Overview

The **V2.5 Director Pipeline** is a production-grade AI system that converts Markdown documents into multi-layer animated presentations. It uses LLM-powered "Director" logic to intelligently partition content, generate narration, and create synchronized visual animations.

---

## V2.5 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         V2.5 Director Pipeline - Full Workflow                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌────────────┐    ┌──────────────┐    ┌─────────────────┐                    │
│   │  Client    │───▶│   /submit_job │───▶│   Job Manager   │                    │
│   │  (Upload)  │    │   (POST)     │    │   (Async Queue) │                    │
│   └────────────┘    └──────────────┘    └────────┬────────┘                    │
│                                                   │                             │
│                ┌──────────────────────────────────┘                             │
│                ▼                                                                │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 1: DOCUMENT PROCESSING                │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │  ┌──────────┐    ┌──────────────┐    ┌────────────────┐       │           │
│   │  │ PDF/DOC  │───▶│ Datalab API  │───▶│  Markdown +    │       │           │
│   │  │ Upload   │    │ (Conversion) │    │  Images        │       │           │
│   │  └──────────┘    └──────────────┘    └───────┬────────┘       │           │
│   └──────────────────────────────────────────────┼────────────────┘           │
│                                                   │                             │
│                ┌──────────────────────────────────┘                             │
│                ▼                                                                │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 2: LLM DIRECTOR                       │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │  ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐  │           │
│   │  │ Smart        │───▶│ Partition       │───▶│ presentation │  │           │
│   │  │ Partitioner  │    │ Director (LLM)  │    │ .json        │  │           │
│   │  │ (55K chunks) │    │ (18 sections)   │    │ (V2.5 Spec)  │  │           │
│   │  └──────────────┘    └─────────────────┘    └──────┬───────┘  │           │
│   └─────────────────────────────────────────────────────┼─────────┘           │
│                                                          │                      │
│         ┌────────────────────────────────────────────────┘                      │
│         │                                                                       │
│         ▼                                                                       │
│   ┌────────────────────────────────────────────────────────────────┐           │
│   │                     PHASE 3: PARALLEL RENDERING                 │           │
│   ├────────────────────────────────────────────────────────────────┤           │
│   │                                                                 │           │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │           │
│   │  │   MANIM      │  │   WAN/KIE    │  │   TTS        │         │           │
│   │  │   Renderer   │  │   Video      │  │   Audio      │         │           │
│   │  │   (Math)     │  │   (Visuals)  │  │   (Voice)    │         │           │
│   │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │           │
│   │         │                 │                 │                  │           │
│   │         ▼                 ▼                 ▼                  │           │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │           │
│   │  │  videos/     │  │  videos/     │  │  audio/      │         │           │
│   │  │  topic_*.mp4 │  │  beat_*.mp4  │  │  *.mp3       │         │           │
│   │  └──────────────┘  └──────────────┘  └──────────────┘         │           │
│   │                                                                 │           │
│   └────────────────────────────────────────────────────────────────┘           │
│                                                                                 │
│         ┌───────────────────────────────────────────────────────────┐          │
│         │                     PHASE 4: AVATAR (Async)               │          │
│         ├───────────────────────────────────────────────────────────┤          │
│         │  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │          │
│         │  │ Narration    │───▶│ Avatar API   │───▶│ avatars/   │  │          │
│         │  │ Segments     │    │ (Kie.ai)     │    │ section_*  │  │          │
│         │  └──────────────┘    └──────────────┘    └────────────┘  │          │
│         └───────────────────────────────────────────────────────────┘          │
│                                                                                 │
│         ┌───────────────────────────────────────────────────────────┐          │
│         │                     OUTPUT: PLAYER                        │          │
│         ├───────────────────────────────────────────────────────────┤          │
│         │  /jobs/<job_id>/player_v2.html  ← Access presentation     │          │
│         │  /jobs/<job_id>/presentation.json                         │          │
│         │  /jobs/<job_id>/videos/                                   │          │
│         │  /jobs/<job_id>/avatars/                                  │          │
│         │  /jobs/<job_id>/audio/                                    │          │
│         └───────────────────────────────────────────────────────────┘          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### V2.5 Director Pipeline
- **Smart Partitioning**: Chunks large documents (55K+ chars) for parallel LLM processing
- **Section-Aware Structure**: 18 distinct section types per V2.5 Director Bible
- **Narration Segments**: LLM generates educator-style explanations with timing
- **Multi-Renderer Support**: Manim for math, WAN for visuals, Avatar for presenter
- **Smart Job Recovery**: Preserves LLM work after server restarts (marks as `completed_with_errors` if `presentation.json` exists)
- **WAN Crash Recovery**: Persists Kie.ai task IDs to `wan_status.json`—recovers completed videos after server crashes without regeneration costs
- **Queued Retries**: All retry actions (Avatar, Video) now respect the global 2-job concurrency limit and queue correctly.
- **Asset Auto-Repair**: Automatically re-downloads missing avatars using existing task IDs—no new billing or regeneration required.

### Renderers
| Renderer | Use Case | Output |
|----------|----------|--------|
| `manim` | Mathematical formulas, graphs, animations | Python → MP4 |
| `video` (WAN/Kie) | Visual storytelling, cinematic scenes | Prompt → MP4 |
| `text_card` | Definitions, bullet points | SVG/HTML layer |
| `avatar` | AI presenter narrating content (11 languages supported - see [Avatar Languages](#-avatar-generation)) | MP4 video |
| `flashcard_set` | Memory/quiz sections | Interactive cards |

### TTS Providers
- **our_tts**: Custom TTS API (69.197.145.4:8000) - Recommended
- **edge_tts**: Microsoft Edge TTS (free, network-dependent)
- **narakeet**: Premium Indian voices (paid)
- **pyttsx3**: Offline Windows TTS (fallback)

---

## Quick Start

### 1. Clone & Configure
```bash
git clone https://github.com/Pramod0605/ai-document-presentation-v2.git
cd ai-document-presentation-v2
cp .env_example .env
# Edit .env with your API keys
```

### 2. System Requirements (for Manim)
Manim requires system-level dependencies:

**Windows:**
```bash
# Install Chocolatey, then:
choco install miktex ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install texlive-full ffmpeg
```

**macOS:**
```bash
brew install --cask mactex
brew install ffmpeg
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Server
```bash
python api/app.py
```
Server runs on `http://localhost:5000` (Docker maps to `5005` externally).

### 5. Access Dashboard
Open [http://localhost:5000/dashboard](http://localhost:5000/dashboard)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | LLM via OpenRouter (Claude/Gemini) |
| `DATALAB_API_KEY` | PDF to Markdown conversion |
| `OUR_TTS_BASE_URL` | Custom TTS API endpoint |
| `OUR_TTS_API_KEY` | Custom TTS API key |
| `KIE_API_KEY` | Kie.ai Video/Avatar generation |

---

## API Endpoints Reference

### 📋 Job Submission & Status

#### `POST /submit_job`
Submit a new presentation job.

**Request (multipart/form-data):**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | File | Yes | - | PDF, DOC, DOCX, ODT, or MD file |
| `subject` | string | No | "General Science" | Subject area |
| `grade` | string | No | "9" | Grade level |
| `pipeline_version` | string | No | "v15_v2_director" | Pipeline: `v15_v2_director` |
| `tts_provider` | string | No | "edge_tts" | TTS: `our_tts`, `edge_tts`, `narakeet` |
| `video_provider` | string | No | "kie" | Video provider |
| `dry_run` | string | No | "false" | Skip actual rendering |
| `skip_wan` | string | No | "false" | Skip WAN video generation |
| `skip_avatar` | string | No | "false" | Skip avatar generation |
| `languages` | string | No | "english" | Comma-separated language names (e.g., "english,hindi,telugu"). See [Avatar Languages](#-avatar-generation) |
| `speaker` | string | No | "default" | Speaker name (e.g., "abhilash") |
| `generation_scope` | string | No | "full" | Scope of generation |
| `job_prefix` | string | No | IP Address | Custom prefix for Job ID (e.g., "Math_Project") |

**Response (200):**
```json
{
  "status": "queued",
  "job_id": "a1b2c3d4",
  "message": "Job submitted successfully",
  "player_url": "/jobs/a1b2c3d4/player_v2.html"
}
```

---

#### `GET /job/<job_id>/status`
Get processing status for a job.

**Response (200):**
```json
{
  "job_id": "a1b2c3d4",
  "status": "processing",
  "blueprint_ready": true,
  "progress": 45,
  "current_step": "Generating TTS Audio",
  "current_phase": "tts_generation",
  "status_message": "Processing section 5 of 18...",
  "steps_completed": 9,
  "total_steps": 20,
  "created_at": "2026-01-23T10:00:00Z",
  "completed_at": null,
  "error": null
}
```

**New Field (February 2026):**
- `blueprint_ready` - **[NEW]** Set to `true` when `presentation.json` is saved. Allows frontend to enable player access early while assets continue rendering.

**Status Values:**
- `pending` - Job queued, waiting to start
- `processing` - Job actively running (LLM, Manim, WAN, Avatar)
- `completed` - Job finished successfully (All assets generated)
- `completed_with_errors` - **[NEW]** LLM Blueprint is done, but some assets failed (use Auto-Repair/Retry)
- `failed` - Job encountered a fatal error (e.g., LLM failure)

#### 🧠 LLM Completion vs. Job Completion
The **LLM Phase** is considered "Complete" when:
1. The **Director's Blueprint** (`presentation.json`) is successfully saved to disk.
2. The `llm_generation` phase in `analytics.json` maps to `completed`.

At this stage, the "Creative Work" is done. The job then moves to **Rendering Phase** (Manim, WAN, Avatar). If the server restarts *after* this point, the job will recover as `completed_with_errors`, preserving your generated content.

---

#### `GET /jobs`
List all jobs with their status.

**Response:**
```json
{
  "jobs": [{
    "job_id": "a1b2c3d4",
    "status": "completed",
    "progress": 100,
    "created_at": "2026-01-23T10:00:00Z",
    "params": {...}
  }],
  "total": 1
}
```

---

#### `GET /job/<job_id>/analytics`
Get detailed analytics for a completed job (LLM costs, timing breakdown, content completeness metrics).

**Response:**
```json
{
  "job_id": "a1b2c3d4",
  "has_analytics": true,
  "analytics": {
    "total_cost_usd": 0.018,
    "total_duration_seconds": 155.23,
    "phases": [...],
    "content_completeness": {...},
    "validation": {...},
    "renderer": {...}
  }
}
```

---

### 🔄 Job Control

#### `POST /job/<job_id>/retry`
Retry a failed job from point of failure or fresh start.

---

#### `POST /job/<job_id>/cancel`
Force cancel a running job.

---

#### `POST /job/<job_id>/retry_phase`
Retry a specific phase for specific sections.

**Request (JSON):**
```json
{
  "phase": "manim_codegen",
  "section_ids": [3, 6, 11],
  "user_feedback": "Make animations slower and use brighter colors"
}
```

**Valid Phases:**
- `manim_codegen` - Regenerate Manim Python code
- `manim_render` - Re-render Manim videos
- `wan_render` - Re-render WAN/Kie videos
- `avatar_generation` - Regenerate avatar videos
- `tts_generation` - Regenerate TTS audio

---

---

### 🎥 Video Regeneration & Retries

#### `POST /jobs/<job_id>/regenerate_and_render`
Regenerate render specs (Manim/WAN) and execute renderers in the background.

**Request (JSON):**
```json
{
  "section_ids": [1, 5],
  "renderers": ["all"],
  "execute": true
}
```

**Response (200):**
```json
{
  "status": "queued",
  "message": "Regeneration started in background",
  "job_id": "a1b2c3d4"
}
```

#### `POST /jobs/<job_id>/rerender`
Request a quick WAN re-render for specific sections (background task).

**Request (JSON):**
```json
{
  "section_ids": ["intro_1"]
}
```

**Response (200):**
```json
{
  "status": "queued",
  "message": "WAN re-render started in background"
}
```

---

### 🧑 Avatar Generation

#### `POST /job/<job_id>/generate_avatar`
Trigger AI Avatar generation for a job. Supports multi-language generation.

**Request Examples:**

**Example 1: Generate avatars for all sections in multiple languages (typical use case)**
```json
{
  "languages": ["english", "hindi", "telugu", "tamil"],
  "speaker": "abhilash"
}
```
Generates avatar videos for **all sections** in English, Hindi, Telugu, and Tamil.

**Example 2: Generate English avatars only (default)**
```json
{
  "languages": ["english"]
}
```
Generates avatars for **all sections** in English.

**Example 3: Retry/Regenerate specific sections only**
```json
{
  "languages": ["hindi"],
  "speaker": "abhilash",
  "target_sections": ["intro_1", "section_5"],
  "force_regenerate": true
}
```
Use `target_sections` when retrying failed sections or selectively updating specific sections.

**Supported Languages:**

| Language Code | Language Name | Notes |
|---------------|---------------|-------|
| `english` | English | Default language (voice cloning) |
| `hindi` | Hindi (हिन्दी) | Indian language |
| `telugu` | Telugu (తెలుగు) | Indian language |
| `tamil` | Tamil (தமிழ்) | Indian language |
| `kannada` | Kannada (ಕನ್ನಡ) | Indian language |
| `malayalam` | Malayalam (മലയാളം) | Indian language |
| `marathi` | Marathi (मराठी) | Indian language |
| `gujarati` | Gujarati (ગુજરાતી) | Indian language |
| `bengali` | Bengali (বাংলা) | Indian language |
| `punjabi` | Punjabi (ਪੰਜਾਬੀ) | Indian language |
| `odia` | Odia (ଓଡ଼ିଆ) | Indian language |
| `assamese` | Assamese (অসমীয়া) | Indian language |

**Parameters:**
- `languages`: Array of language names (e.g., `["english", "hindi", "telugu"]`). See table above for supported codes.
- `speaker`: (Optional) Voice name from the supported list.
- `target_sections`: (Optional) Array of section IDs. **Only needed for retries/selective regeneration**. If omitted, processes **all sections**.
- `force_regenerate`: (Optional) If true, overwrites existing avatars. Typically used with `target_sections` for retries.

---

#### `GET /job/<job_id>/avatar_status`
Get avatar generation progress.

**Response:**
```json
{
  "state": "processing",
  "message": "Generating avatar for section 5...",
  "progress": 35,
  "details": {
    "total_sections": 18,
    "completed_sections": 6,
    "failed_sections": []
  }
}
```

---

#### `GET /job/<job_id>/wan_status` **[NEW - February 2026]**
Get WAN video generation progress (real-time tracking).

**Response:**
```json
{
  "state": "processing",
  "total_beats": 10,
  "completed_beats": 7,
  "failed_beats": 1,
  "progress_percent": 70,
  "started_at": "2026-02-10T18:00:00",
  "updated_at": "2026-02-10T18:36:00",
  "details": {
    "pending": [],
    "in_progress": [],
    "completed": ["topic_1_beat_0", "topic_1_beat_1", ...],
    "failed": ["topic_2_beat_3"],
    "errors": {"topic_2_beat_3": "Generation failed"}
  }
}
```

**Status States:**
- `processing` - Generation in progress
- `completed` - All beats succeeded
- `completed_with_errors` - Some beats failed
- `not_found` - WAN generation not started (404)

---

#### `POST /job/<job_id>/regenerate_failed_avatars`
Regenerate only failed/missing avatars.

---

#### `POST /job/<job_id>/regenerate_avatar/<section_id>`
Regenerate avatar for a specific section.

---

### 📐 Manim Regeneration

#### `POST /regenerate_manim/<job_id>`
Regenerate Manim code for specific sections with optional user feedback.

**Request (JSON):**
```json
{
  "section_id": 3,
  "user_feedback": "Make animations slower, use brighter colors"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Regenerated 5 Manim sections",
  "sections": [3, 6, 9, 12, 15]
}
```

---

### 🔧 Metadata & Diagnostic Tools

#### `POST /api/repair-missing-assets/<job_id>` ✨ **NEW**
**Automated Asset Recovery** - Scans `presentation.json`, identifies missing local `.mp4` files, and re-downloads them from the remote server using existing Task IDs.
- ✅ **Cost-Efficiency:** Does NOT trigger a new generation; uses already-paid-for tasks.
- ✅ **Deep Validation:** Verifies the task is actually `completed` on the remote server before attempting download.
- ✅ **Actionable Repair:** Recommended follow-up action when `sanity-report` identifies missing avatars.

**Response:**
```json
{
  "status": "success",
  "repaired_count": 3,
  "details": [
    {"section_id": "1", "type": "default", "status": "repaired"},
    {"section_id": "5", "type": "lang_hindi", "status": "repaired"}
  ],
  "message": "Successfully repaired 3 avatar files from remote server."
}
```

---

#### `POST /api/repair-metadata/<job_id>`
Surgically repair presentation.json by scanning for orphaned assets on disk and stitching them back into JSON.

**Response:**
```json
{
  "status": "repaired",
  "updates": 12,
  "found_videos": ["topic_1.mp4", "topic_2.mp4"],
  "found_avatars": ["section_1_avatar.mp4"]
}
```

---

#### `GET /api/sanity-report/<job_id>` ✨ **NEW**
**100% truthful asset validation** - Provides comprehensive read-only truth report by scanning directories and comparing against JSON references. Returns orphaned files, missing files, and accuracy metrics.

**Response:**
```json
{
  "job_id": "6355bd5b",
  "accuracy": 76.19,
  "summary": {
    "videos_on_disk": 9,
    "videos_in_json": 14,
    "missing_videos": 5,
    "orphaned_videos": 0,
    "avatars_in_json": 7,
    "avatars_on_disk": 7,
    "matched_videos": 9
  },
  "orphaned": {
    "videos": [],
    "avatars": []
  },
  "missing": {
    "videos": ["topic_7_seg_1_beat_1", "topic_7_seg_2_beat_1"],
    "avatars": []
  },
  "sections": [
    {
      "section_id": "7",
      "section_type": "recap",
      "renderer": "video",
      "title": "Lesson Recap",
      "segments_with_beats": 5,
      "total_beat_videos": 5,
      "videos_in_json": ["topic_7_seg_1_beat_1", ...],
      "videos_on_disk": [],
      "videos_missing": ["topic_7_seg_1_beat_1", ...],
      "videos_orphaned": [],
      "avatar_status": "found"
    }
  ]
}
```

**Key Features:**
- ✅ Scans all directories (videos/, avatars/, images/)
- ✅ **Segment-level beat video validation** (scans `narration.segments[].beat_videos[]`)
- ✅ Calculates accuracy percentage
- ✅ Read-only (does not mutate presentation.json)

---

### 📝 Review & Feedback

#### `POST /submit_review`
Submit a review for a specific job section (saves to `reviews.json`).

---

#### `POST /job/<job_id>/submit_review`
Submit section-specific review.

---

#### `POST /recreate_job_from_review`
Trigger regeneration of a job (or specific sections) based on submitted reviews.

---

### 📁 Static File Serving

#### `GET /dashboard`
Serve the job management dashboard UI.

#### `GET /sanity_check.html`
Serve the sanity check tool for visual validation of presentation structure.

**Usage:** `http://localhost:5000/sanity_check.html?job=<job_id>`

#### `GET /player/<filename>`
Serve player assets (legacy).

#### `GET /player_v2/<filename>`
Serve V2.5 player files.

#### `GET /jobs/<job_id>/`
Serve job-specific player (index.html).

#### `GET /jobs/<job_id>/<filename>`
Serve any file from job folder (videos, audio, avatars, presentation.json, etc.).

---

## Accessing Job Files

### Player Access
After a job completes, access the presentation player at:
```
http://<server>:<port>/jobs/<job_id>/player_v2.html
```

**Production Example:**
```
http://69.197.145.4:5005/jobs/a1b2c3d4/player_v2.html
```

### Sanity Check
Visual validation of presentation structure:
```
http://<server>:<port>/sanity_check.html?job=<job_id>
```

### Direct File Access
All job files are accessible via the `/jobs/<job_id>/` route:

| File | URL Pattern |
|------|-------------|
| Presentation JSON | `/jobs/<job_id>/presentation.json` |
| Analytics | `/jobs/<job_id>/analytics.json` |
| Source Markdown | `/jobs/<job_id>/source_markdown.md` |
| Videos | `/jobs/<job_id>/videos/<filename>.mp4` |
| Avatars | `/jobs/<job_id>/avatars/<filename>.mp4` |
| Audio | `/jobs/<job_id>/audio/<filename>.mp3` |
| Manim Code | `/jobs/<job_id>/manim_code/<filename>.py` |

---

## Job Output Structure

Each job creates the following folder structure:
```
player/jobs/{job_id}/
├── presentation.json       # All sections with narration, timing, visual specs
├── analytics.json          # Timing, token usage, render statistics
├── source_markdown.md      # Original document converted to markdown
├── source_document.pdf     # Backup of uploaded file
├── avatar_status.json      # Avatar generation progress
├── player_v2.html          # Self-contained player
├── player_v2.js            # Player logic
├── index.html              # Entry point
├── artifacts/              # LLM output artifacts
│   ├── 01_chunker.json
│   ├── 02_planner.json
│   └── ...
├── manim_code/             # Generated Manim Python scripts
│   └── section_*.py
├── videos/                 # Rendered video animations
│   ├── topic_*.mp4         # Per-section videos
│   └── topic_*_beat_*.mp4  # Per-beat videos (V2.5)
├── audio/                  # TTS audio files
│   └── section_*.mp3
├── avatars/                # AI avatar videos
│   ├── metadata.json       # Map of languages and speakers
│   ├── en/                 # Default (English) avatars
│   │   └── section_*_avatar.mp4
│   └── {lang}/             # Language subfolders (e.g., hi, te)
│       └── section_*_avatar.mp4
└── images/                 # Extracted/processed images
    └── *.png
```

---

## Pipeline Modes

| Mode | Description |
|------|-------------|
| `v15_v2_director` | Full V2.5 Director with smart partitioning (default) |
| `v15` | V1.5 Optimized pipeline |
| `v14` | Split Director pipeline |

---

## Server Operations & Maintenance

### Docker Management
```bash
# Start/Rebuild Server
docker compose up -d --build

# Stop Server
docker compose down

# Restart Server
docker compose restart

# View live logs
docker compose logs -f
```

### Code Updates
```bash
git pull
docker compose up -d --build
```

### Production Deployment (Windows)
Use the provided PowerShell scripts:

| Script | Description |
|--------|-------------|
| `deploy_prod.ps1` | Pull latest code and restart container |
| `production_login.ps1` | SSH into production server |
| `production_logs.ps1` | View live production logs |
| `production_docker_shell.ps1` | Open bash inside container |
| `production_inspect_job.ps1 <job_id>` | Inspect job files on server |

---

## Technical Documentation

For deep-dive architecture and implementation details:
- **[V2.5 Director Bible](v2.5_Director_Bible.md):** The single source of truth for pipeline specification
- **[V2.5 Director Pipeline Spec](docs/v2.5_Director_Pipeline_Technical_Doc.md):** Full architecture, Data Flow, and Agent Logic
- **[Player V2.5 Technical Spec](player_v2_technical.md):** Browser rendering logic, Compliance Matrix, and Features

---

## Utility Scripts

| Script | Usage | Description |
|--------|-------|-------------|
| `verify_job_content.py` | `python verify_job_content.py <JOB_ID>` | Validate Director Bible compliance |
| `check_job.py` | `python check_job.py <JOB_ID>` | Quick job status check |
| `reset_jobs.py` | `python reset_jobs.py` | Reset stuck "processing" jobs to "failed" |
| `fix_job_status.py` | `python fix_job_status.py` | Manually fix job entries |
| `repair_all_avatars.py` | `python scripts/repair_all_avatars.py` | [NEW] Bulk repair for ALL historical jobs |
| `deep_fidelity_analysis.py` | `python scripts/deep_fidelity_analysis.py <JOB_ID>` | Analyze job quality |

---

## License

MIT License
