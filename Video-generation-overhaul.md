Implementation Plan: Video Generation Overhaul (V2.5 Bible Aligned)
Goal: Fix duplicate prompts + WAN 15s limit + Batched Kie.ai + Regeneration Priority: HIGH Bible Reference: 
v2.5_Director_Bible.md
 Validation Job: a75fe79d

Real Example: Job a75fe79d Analysis
Current Structure (Working ✅)
// Section 3, Segment with beat_videos array
{
  "segment_id": "seg_1",
  "text": "Namaste students! Today we begin a fascinating journey...",
  "duration_seconds": 23.35,
  "display_directives": {
    "text_layer": "show",
    "visual_layer": "hide",   // TEACH segment
    "avatar_layer": "show"
  },
  "beat_videos": ["seg_1_beat_1", "seg_1_beat_2"]  // Split into 2 beats (23s > 15s)
}
THE BUG: All Prompts Are Identical ❌
// video_prompts array - ALL 16 BEATS USE SAME PROMPT!
{
  "beat_id": "seg_1_beat_1",
  "prompt": "Create a dynamic video sequence. Start with a time-lapse of a bustling Indian city like Mumbai...",
  "duration_hint": 15
},
{
  "beat_id": "seg_2_beat_1",
  "prompt": "Create a dynamic video sequence. Start with a time-lapse of a bustling Indian city like Mumbai...",  // SAME!
  "duration_hint": 15
},
{
  "beat_id": "seg_4_beat_1", 
  "prompt": "Create a dynamic video sequence. Start with a time-lapse of a bustling Indian city like Mumbai...",  // SAME!
  "duration_hint": 15
}
// ... all 16 beats have IDENTICAL prompts
Root Cause
The Director LLM outputs ONE 
video_prompt
 per SECTION in render_spec.video_prompts:

"render_spec": {
  "video_prompts": ["Create a dynamic video sequence..."]  // ONLY 1 PROMPT for 10 segments!
}
Then 
_apply_sync_splitter()
 in 
unified_director_generator.py
 copies this to ALL beats:

base_prompt = v_prompts[idx % len(v_prompts)]  # Cycles through 1 prompt = ALWAYS SAME
The Fix: Director Must Output 1 Prompt Per SHOW Segment
Target Structure (After Fix)
// Director outputs segment-specific prompts
"render_spec": {
  "segment_specs": [
    {
      "segment_id": "seg_2",
      "duration_seconds": 23.86,
      "video_prompt": "Show the four pillars of life with animated icons: a green leaf glowing for nutrition, pink lungs expanding for respiration, blue interconnected vessels for transportation, and a water droplet for excretion. Camera slowly pans across each icon as they illuminate. (80+ words)"
    },
    {
      "segment_id": "seg_4",
      "duration_seconds": 21.83,
      "video_prompt": "Zoom into a single cell, revealing a vibrant microscopic world. Show tiny molecular 'workers' - enzymes as glowing spheres - mixing chemicals in the cytoplasm. ATP molecules spark with energy as they form. Mitochondria pulse with golden light. The organized dance of molecules maintains the cell's beautiful structure. (80+ words)"
    },
    {
      "segment_id": "seg_6",
      "duration_seconds": 14.22,
      "video_prompt": "Animate a piece of Indian roti entering the body. Show it breaking down in the stomach into glowing glucose particles. These particles travel through blood vessels to a cell, where they enter and release bright sparks of energy (ATP), powering thoughts and heartbeats. (80+ words)"
    }
    // ... unique prompt for each SHOW segment
  ]
}
Target Beat Structure (After Splitting)
// For seg_4 (21.83s > 15s → 2 beats)
{
  "beat_id": "seg_4_beat_1",
  "segment_id": "seg_4",
  "prompt": "Zoom into a single cell, revealing a vibrant microscopic world. Show tiny molecular 'workers' - enzymes as glowing spheres - mixing chemicals in the cytoplasm. ATP molecules spark with energy as they form. (Part 1 of 2)",
  "duration_hint": 10.9
},
{
  "beat_id": "seg_4_beat_2",
  "segment_id": "seg_4",
  "prompt": "Keeping the previous scene exactly the same, continue showing mitochondria pulsing with golden light. The organized dance of molecules maintains the cell's beautiful structure as the camera slowly pulls back. (Part 2 of 2)",
  "duration_hint": 10.9
}
Part 1: Director Prompt Fix
1.1 Files to Modify
[MODIFY] 
director_partition_prompt.txt
Replace render_spec schema (Lines 114-120):

BEFORE:

"render_spec": {
  "manim_scene_spec": "Detailed string (80+ words)...",
  "video_prompts": ["Detailed cinematic prompt (80+ words)..."]
}
AFTER:

"render_spec": {
  "segment_specs": [
    {
      "segment_id": "seg_2",
      "renderer": "manim|video",
      "duration_seconds": 23.86,
      "manim_scene_spec": "For manim: 80+ word description...",
      "video_prompt": "For WAN: 80+ word cinematic prompt..."
    }
  ]
}
Add New Rule (After Line 51 - CRITICAL):

### SEGMENT_SPECS REQUIREMENT (MANDATORY)
> [!CAUTION]
> You MUST generate ONE segment_spec for EACH SHOW segment (visual_layer = "show").
> DO NOT generate a single prompt for the entire section!
**RULES:**
1. Count your SHOW segments (seg_2, seg_4, seg_6, seg_8, seg_10...)
2. Generate that many segment_specs
3. Each segment_spec must be UNIQUE and describe what happens during THAT segment's narration
4. Each prompt must be 80+ words
**EXAMPLE: Section with 5 SHOW segments:**
```json
"segment_specs": [
  {"segment_id": "seg_2", "renderer": "video", "duration_seconds": 23.86, "video_prompt": "Unique 80+ word prompt for seg_2..."},
  {"segment_id": "seg_4", "renderer": "video", "duration_seconds": 21.83, "video_prompt": "Unique 80+ word prompt for seg_4..."},
  {"segment_id": "seg_6", "renderer": "video", "duration_seconds": 14.22, "video_prompt": "Unique 80+ word prompt for seg_6..."},
  {"segment_id": "seg_8", "renderer": "video", "duration_seconds": 18.78, "video_prompt": "Unique 80+ word prompt for seg_8..."},
  {"segment_id": "seg_10", "renderer": "video", "duration_seconds": 18.78, "video_prompt": "Unique 80+ word prompt for seg_10..."}
]
FOR WAN VIDEOS > 15 SECONDS: If a segment's duration_seconds > 15, you MUST provide continuation prompts:

{
  "segment_id": "seg_4",
  "renderer": "video",
  "duration_seconds": 28,
  "beats": [
    {"beat_id": "seg_4_beat_1", "duration": 14, "prompt": "First part (80+ words)..."},
    {"beat_id": "seg_4_beat_2", "duration": 14, "prompt": "Keeping the scene exactly the same, continue showing... (80+ words)"}
  ]
}
---
#### [MODIFY] [unified_director_generator.py](file:///c:/Users/email/Downloads/AI-Document-presentation/ai-doc-presentation/core/unified_director_generator.py)
**Location**: [_apply_sync_splitter()](file:///c:/Users/email/Downloads/AI-Document-presentation/ai-doc-presentation/core/partition_director_generator.py#441-533) function
**BEFORE (Bug):**
```python
# This copies the SAME prompt to ALL beats
base_prompt = v_prompts[idx % len(v_prompts)]
for i in range(num_beats):
    final_video_prompts.append({
        "beat_id": f"{seg_id}_beat_{i+1}",
        "prompt": f"{consistency_prefix}{base_prompt} (Part {i+1} of {num_beats})"
    })
AFTER (Fix):

def _apply_sync_splitter(self, section: dict) -> dict:
    """
    Map each SHOW segment to its specific render spec.
    - If LLM provides segment_specs: use those (1 prompt per segment)
    - If LLM provides beats: use those (pre-split for > 15s segments)
    - Fallback: auto-split long segments with continuation prefix
    """
    segments = section.get("narration", {}).get("segments", [])
    segment_specs = section.get("render_spec", {}).get("segment_specs", [])
    
    # Build segment_id -> spec map
    spec_map = {spec["segment_id"]: spec for spec in segment_specs if "segment_id" in spec}
    
    final_video_prompts = []
    final_manim_specs = []
    
    for seg in segments:
        seg_id = seg.get("segment_id")
        directives = seg.get("display_directives", {})
        duration = seg.get("duration_seconds", 15)
        
        # Only SHOW segments need render specs
        if directives.get("visual_layer") != "show":
            continue
        
        spec = spec_map.get(seg_id)
        
        if not spec:
            logger.warning(f"[Sync Splitter] No spec for SHOW segment {seg_id}")
            continue
        
        renderer = spec.get("renderer", "video")
        
        if renderer == "manim":
            # Manim: 1 spec per segment (no 15s limit)
            final_manim_specs.append({
                "segment_id": seg_id,
                "duration_seconds": duration,
                "manim_scene_spec": spec.get("manim_scene_spec", "")
            })
            seg["video_file"] = f"topic_{section['section_id']}_{seg_id}.mp4"
            
        else:  # video/wan
            # Check if LLM already provided beats
            beats = spec.get("beats", [])
            
            if beats:
                # Use LLM-provided beats
                for beat in beats:
                    beat["segment_id"] = seg_id
                    final_video_prompts.append(beat)
                seg["beat_videos"] = [b["beat_id"] for b in beats]
            else:
                # Auto-split if > 15s
                video_prompt = spec.get("video_prompt", "")
                num_beats = max(1, math.ceil(duration / 15))
                beat_duration = duration / num_beats
                
                beat_ids = []
                for i in range(num_beats):
                    beat_id = f"{seg_id}_beat_{i+1}"
                    prefix = "" if i == 0 else "Keeping the previous scene exactly the same, continue showing: "
                    suffix = f" (Part {i+1} of {num_beats})" if num_beats > 1 else ""
                    
                    final_video_prompts.append({
                        "beat_id": beat_id,
                        "segment_id": seg_id,
                        "prompt": prefix + video_prompt + suffix,
                        "duration_hint": min(15, beat_duration)
                    })
                    beat_ids.append(beat_id)
                
                seg["beat_videos"] = beat_ids
    
    # Store for downstream processing
    section["_wan_beats"] = final_video_prompts
    section["_manim_specs"] = final_manim_specs
    section["video_prompts"] = final_video_prompts  # For compatibility
    
    return section
1.2 Validator Updates
[MODIFY] 
v25_validator.py
Add segment_specs validation:

def validate_segment_specs(self, section: dict) -> List[str]:
    """Validate that each SHOW segment has a unique render spec."""
    errors = []
    
    segments = section.get("narration", {}).get("segments", [])
    segment_specs = section.get("render_spec", {}).get("segment_specs", [])
    
    # Get SHOW segment IDs
    show_seg_ids = {
        seg["segment_id"] for seg in segments
        if seg.get("display_directives", {}).get("visual_layer") == "show"
    }
    
    if not show_seg_ids:
        return errors  # No SHOW segments
    
    # Check for missing specs
    spec_seg_ids = {spec["segment_id"] for spec in segment_specs if "segment_id" in spec}
    missing = show_seg_ids - spec_seg_ids
    
    if missing:
        errors.append(
            f"Section '{section.get('title')}': Missing segment_specs for: {missing}"
        )
    
    # Check for duplicate prompts (THE BUG)
    prompts = []
    for spec in segment_specs:
        prompt = spec.get("video_prompt", "") or spec.get("manim_scene_spec", "")
        if prompt:
            prompts.append(prompt)
    
    unique_prompts = set(prompts)
    if len(unique_prompts) < len(prompts) * 0.5:  # More than 50% duplicates
        errors.append(
            f"Section '{section.get('title')}': DUPLICATE PROMPTS DETECTED! "
            f"{len(prompts)} prompts but only {len(unique_prompts)} unique."
        )
    
    return errors
Part 2: Batched Kie.ai WAN Generation
2.1 Example from Job a75fe79d
Section 3 has 16 beat videos to generate:

Beat 1-5: seg_1 through seg_5 (5 beats)
Beat 6-10: seg_6 through seg_10 (5 beats + continuation beats)
With batch size 15, interval 15s:

Batch 1 (0s):    Submit beats 1-15 → Get 15 task_ids
Wait 15s
Batch 2 (15s):   Submit beat 16 → Get 1 task_id
Poll all 16 tasks → Download videos
2.2 New File: kie_batch_generator.py
"""
Batched Kie.ai WAN Video Generator
- 15 concurrent requests per batch
- 15 second interval between batches
- Auto-retry failed tasks up to 3 times
"""
BATCH_SIZE = 15
BATCH_INTERVAL_SECONDS = 15
MAX_RETRIES_PER_TASK = 3
class KieBatchGenerator:
    def generate_section_videos(self, section: dict, output_dir: str) -> Dict:
        """Generate all WAN videos for a section using batched API calls."""
        
        wan_beats = section.get("video_prompts", [])
        
        # Group into batches of 15
        batches = [wan_beats[i:i+BATCH_SIZE] for i in range(0, len(wan_beats), BATCH_SIZE)]
        
        all_task_ids = []
        
        for batch_idx, batch in enumerate(batches):
            # Submit batch
            task_ids = self._submit_batch(batch, output_dir)
            all_task_ids.extend(task_ids)
            
            # Wait between batches (not after last)
            if batch_idx < len(batches) - 1:
                time.sleep(BATCH_INTERVAL_SECONDS)
        
        # Poll all tasks
        results = self._poll_and_download_all(all_task_ids)
        
        return results
Part 3: Video Regeneration API
3.1 Endpoints
Endpoint	Method	Purpose
/api/job/<id>/regenerate_failed	POST	Find and regenerate corrupt/missing videos
/api/job/<id>/regenerate_section/<section_id>	POST	Regenerate all videos for section (overwrite)
/api/job/<id>/regenerate_beat/<beat_id>	POST	Regenerate single beat video
3.2 Detection Logic
def find_failed_videos(job_dir: str) -> List[Dict]:
    """Identify videos that need regeneration."""
    failed = []
    
    videos_dir = Path(job_dir) / "videos"
    
    for video_file in videos_dir.glob("*.mp4"):
        size = video_file.stat().st_size
        
        if size < 10_000:  # < 10KB = corrupt placeholder
            failed.append({
                "path": str(video_file),
                "reason": "corrupt",
                "size_kb": size / 1024
            })
    
    return failed
Part 4: Final Validation Checklist
Check	Expected	Actual (Job a75fe79d)
Segment count	10 segments	✅ 10 segments
SHOW segments	5 (seg_2, seg_4, seg_6, seg_8, seg_10)	✅ Correct
Unique prompts	5+ unique	❌ 1 unique (BUG)
Beat splitting	seg_1 (23s) → 2 beats	✅ Working
Beat video paths	topic_3_seg_1_beat_1.mp4	✅ Generated
Part 5: Rollout Steps
Update Director Prompt → Add segment_specs schema
Update Sync Splitter → Map by segment_id
Add Validator → Detect duplicate prompts
Create Batch Generator → 15 concurrent, 15s intervals
Create Regenerator → API for retry
Test with Job a75fe79d → Verify fix
Deploy to Production
Summary
Problem	Current	Fix
Duplicate prompts	1 prompt for entire section	1 prompt per SHOW segment
WAN 15s limit	Already handled	Already handled ✅
Beat splitting	Working	Keep as-is ✅
Validator	No duplicate check	Add duplicate detection
Batch API	3 concurrent	15 concurrent, 15s interval
Failed videos	Manual retry	API endpoints
