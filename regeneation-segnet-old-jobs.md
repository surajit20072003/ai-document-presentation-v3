Implementation Plan: Director Regeneration Phase
Goal
Add a 5th retry option called "Director (Re-generate Prompts)" that:

Re-runs the Director LLM for selected sections
Updates render_spec.segment_specs with new unique visual prompts
Saves updated 
presentation.json
 (ready for WAN regeneration)
Analysis
What Already Exists
Component	Location	Reusable?
Content Worker	partition_director_generator._run_content_worker_sync()	✅ Core logic
Sync Splitter	partition_director_generator._apply_sync_splitter()	✅ Beat mapping
V25 Validator	v25_validator.validate_content_chunk()	✅ No changes needed
Director Prompt	
core/prompts/director_partition_prompt.txt
✅ Already updated
New Code Required
Component	Purpose	Lines Est.
_retry_director_regen()	New handler function in 
app.py
~60 lines
Dashboard option	Add to dropdown	1 line
Route handler	Add to 
retry_phase
 switch	2 lines
Total New Code: ~65 lines (No new validators, no new prompts)

Proposed Changes
1. Dashboard Update
File: 
dashboard.html

<option value="director_regen">🔄 Director (Re-generate Prompts)</option>
2. Route Handler Update
File: 
app.py

elif phase == "director_regen":
    result = _retry_director_regen(job_id, job_folder, presentation, section_ids)
3. New Handler Function
File: 
app.py
 (after 
_retry_manim_render
)

def _retry_director_regen(job_id: str, job_folder: Path, presentation: dict, section_ids: list = None) -> dict:
    """
    Re-run Director LLM for selected sections to generate NEW segment_specs.
    Uses the updated V2.5 prompt that outputs unique visual descriptions per segment.
    """
    from core.partition_director_generator import PartitionDirectorGenerator
    from core.config import GeneratorConfig
    
    results = {"success": [], "failed": [], "skipped": []}
    generator = PartitionDirectorGenerator(GeneratorConfig())
    
    for section in presentation.get("sections", []):
        section_id = section.get("section_id")
        renderer = section.get("renderer", "none")
        section_type = section.get("section_type", "")
        
        # Only regenerate for video/content sections (not intro, quiz, etc.)
        if section_type in ["intro", "summary", "quiz", "memory"]:
            results["skipped"].append({"section_id": section_id, "reason": "Global section"})
            continue
            
        if section_ids and section_id not in section_ids:
            results["skipped"].append({"section_id": section_id, "reason": "Not in list"})
            continue
        
        try:
            # Build chunk from existing section content
            chunk = {
                "title": section.get("title", f"Section {section_id}"),
                "content": section.get("content", "")
            }
            
            if not chunk["content"]:
                results["skipped"].append({"section_id": section_id, "reason": "No content"})
                continue
            
            print(f"[DIRECTOR-REGEN] Re-generating prompts for section {section_id}...")
            
            # Call the content worker (reuses existing logic)
            new_sections = generator._run_content_worker_sync(
                index=section_id,
                chunk=chunk,
                full_context="",  # Not needed for regen
                subject=presentation.get("metadata", {}).get("subject", "Science"),
                grade=presentation.get("metadata", {}).get("grade", "Grade 10"),
                images_list=presentation.get("metadata", {}).get("images", []),
                output_dir=str(job_folder)
            )
            
            if new_sections and len(new_sections) > 0:
                new_sec = new_sections[0]
                # Preserve section_id and merge new render_spec
                section["render_spec"] = new_sec.get("render_spec", {})
                section["narration"] = new_sec.get("narration", section.get("narration"))
                
                results["success"].append({
                    "section_id": section_id,
                    "segment_specs_count": len(new_sec.get("render_spec", {}).get("segment_specs", []))
                })
            else:
                results["failed"].append({"section_id": section_id, "error": "Empty response"})
                
        except Exception as e:
            results["failed"].append({"section_id": section_id, "error": str(e)})
    
    return results
Workflow After Implementation
1. User selects "🔄 Director (Re-generate Prompts)" for job a75fe79d
2. System re-runs Director LLM for each content section
3. New segment_specs with unique prompts are saved to presentation.json
4. User then selects "🎬 WAN Video Rendering" to use the NEW prompts
5. WAN videos generated with proper beat-based structure
Rollout Steps
 Add director_regen option to 
dashboard.html
 Add route handler in 
app.py
 
retry_phase
 Implement _retry_director_regen() function
 Test on job a75fe79d
 Verify new segment_specs in presentation.json