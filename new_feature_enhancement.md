Implementation Plan - Production Enhancements
Goal
Implement 4 critical UX and infrastructure improvements for production readiness.

Feature 1: Namaste Only in Intro Section
Problem
"Namaste" greeting appears in every section, making it repetitive and unnatural.

Proposed Solution
Modify LLM prompt to conditionally include "Namaste" based on section type.

Implementation
Files to Modify
core/prompts/unified_system_prompt_CURRENT.txt

Add section_type conditional instruction
"Use 'Namaste' ONLY if section_type === 'intro'"
core/partition_director_generator.py

Ensure section_type is passed to narration generator
Verify "intro" detection logic
Changes
# In prompt template
if section_type == "intro":
    narration_start = "Namaste! Welcome to..."
else:
    narration_start = "Let's explore..."  # Natural opener, no Namaste
Testing
Mode: dry_run=true
Generate job.
Inspect 
presentation.json
 for "Namaste" in intros vs others.
Complexity: Low (2-3 hours)
Feature 2: Lively Section Transitions
Problem
Transitions between sections are instant and robotic - no narrative bridge.

Proposed Solution
Generate a short "transition segment" at the end of each section that previews the next section.

Design
Transition Segment Structure
{
  "segment_id": "transition_to_5",
  "type": "transition",
  "narration": "Now that we understand the basics, let's dive into the exciting world of...",
  "duration": 3.0,
  "next_section_title": "Advanced Concepts"
}
Where to Add
At end of each section (except last section)
Duration: 2-4 seconds
Content: Preview of next section's topic
Implementation
Files to Modify
core/prompts/unified_system_prompt_CURRENT.txt

Add instruction to generate transition_narration field for each section (except last).
"Generate a brief, lively transition (1-2 sentences) bridging to the next section."
core/partition_director_generator.py

Ensure transition_narration is extracted from LLM JSON output.
Pass this field to 
presentation.json
.
player/player_v2.js

Update playback logic to handle transition_narration.
Play transition audio/text after section content finishes.
Testing
Mode: dry_run=true
Generate job, inspect 
presentation.json
 for transition_narration.
Verify player handles it (mock audio if needed).
Complexity: Medium (4-6 hours)
Feature 3: Admin Panel & Configuration Management
Problem
No UI for managing prompts, endpoints, or restarting Docker without SSH.

Proposed Solution
Web-based admin panel with CRUD operations for prompts/config + Docker restart.

Design
Admin Panel Features
Prompt Editor

List all prompt files
Edit in-browser
Save changes
Version history
Configuration Manager

Edit .env variables (API keys, endpoints)
Update service IPs (TTS, WAN, Avatar APIs)
Save and reload config
Docker Control

Restart API container
View container logs (last 100 lines)
Container health status
System Info

Current pipeline version
Uptime
Recent job stats
Implementation
New Files
admin_panel/index.html

Modern UI (dark theme, glassmorphic)
Tabs for: Prompts | Config | Docker | System
admin_panel/admin.js

API calls to admin endpoints
CodeMirror for prompt editing
Form handling for config
admin_panel/admin.css

Consistent styling with dashboard
New Routes in 
api/app.py
# Admin endpoints
@app.route('/admin')
def admin_panel():
    """Serve admin panel HTML"""
    
@app.route('/admin/prompts', methods=['GET'])
def list_prompts():
    """List all prompt files in core/prompts/"""
    
@app.route('/admin/prompts/<filename>', methods=['GET', 'PUT'])
def edit_prompt(filename):
    """Read or update a prompt file"""
    
@app.route('/admin/config', methods=['GET', 'PUT'])
def manage_config():
    """Read or update .env configuration"""
    
@app.route('/admin/docker/restart', methods=['POST'])
def restart_docker():
    """Restart Docker container"""
    # os.system('docker restart ai-document-presentation-v2-api-1')
    
@app.route('/admin/docker/logs', methods=['GET'])
def get_docker_logs():
    """Get last N lines of Docker logs"""
Security
Authentication: Simple API Key

check for x-admin-key header matching ADMIN_API_KEY in .env.
Simple and effective for internal service calls.
Testing
Mode: dry_run=true (where applicable)
Validate endpoint security.
Test Docker restart (ensure script permissions).
Complexity: High (12-16 hours)
Feature 4: Multi-Language Avatar Support (PARKED)
NOTE

This feature is parked for future discussion as per user feedback.

Status
Schema Agreed: New 
avatars
 object structure in 
presentation.json
.
Implementation: Deferred.
Future Design (Saved for later)
presentation.json Schema Enhancement
{
  "section_id": "3",
  "avatars": {
    "english": "section_3_avatar_en.mp4",
    "kannada": "section_3_avatar_kn.mp4"
  }
}
User Review Required
IMPORTANT

Please review the implementation approach for each feature

Questions for Clarification
Feature 1: Namaste

✅ Simple prompt modification - Proceed?
Feature 2: Transitions

Should transitions be mandatory or optional?
Preferred transition duration (2-4 seconds)?
Should LLM generate transition text or use templates?
Feature 3: Admin Panel

Required authentication level (API Key vs Basic Auth)?
Should Docker restart be server-wide or container-specific?
Need audit log for config changes?
Feature 4: Multi-Language

Which translation service: LLM or Google Translate?
How many workers for parallel generation (4, 8, 16)?
Should narration text be translated or user-provided?
Language codes format: ISO (en, kn, hi) or full names?
Proposed Implementation Order
Feature 1: Namaste Control (1-2 hours)
Test with 
dry_run
.
Feature 2: Section Transitions (3-4 hours)
Update 
unified_system_prompt_CURRENT.txt
.
Update Player V2.
Feature 3: Admin Panel (8-12 hours)
Implement simple API Key auth.
Total Active Work: ~12-18 hours (Feature 4 Parked)

Verification Plan
After Each Feature
Unit tests for new functions
Integration test with full pipeline
Manual QA in player
Update documentation
Final Verification
Generate test job with all features enabled
Test multi-language switching
Verify transitions work smoothly
Use admin panel to modify prompts
Restart Docker via admin panel

Comment
Ctrl+Alt+M
