"""
V1.5 Unified Pipeline Orchestrator
Uses Single LLM Architecture (UnifiedContentGenerator) + Explicit Renderer Bridging.
"""

import logging
import json
import time
import os
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable

from core.unified_content_generator import (
    generate_presentation, 
    transform_to_player_schema,
    GeneratorConfig
)
from core.unified_director_generator import generate_director_presentation
from core.partition_director_generator import PartitionDirectorGenerator # New Phase 7
from core.validators.job_certifier import JobCertifier # Automated Certification
from core.analytics import create_tracker, PipelineAnalytics, AnalyticsTracker
from core.renderer_executor import enforce_renderer_policy, render_all_topics
from core.tts_duration import update_durations_simplified, TTSProvider
from core.agents.manim_code_generator import ManimCodeGenerator, integrate_manim_code_into_section
from core.agents.avatar_generator import AvatarGenerator
from core.image_processor import save_datalab_images, extract_image_refs_from_markdown
from core.locks import presentation_lock  # V2.5 FIX: Thread-safe JSON writes

logger = logging.getLogger(__name__)

class PipelineUnifiedError(Exception):
    def __init__(self, message: str, phase: str):
        super().__init__(message)
        self.phase = phase

def process_markdown_unified(
    markdown_content: str,
    subject: str,
    grade: str,
    job_id: str,
    update_status_callback=None,
    generate_tts: bool = False,
    output_dir: Optional[Path] = None,
    tts_provider: TTSProvider = "our_tts",
    dry_run: bool = False,
    skip_wan: bool = False,
    skip_avatar: bool = False,
    images_dict: Optional[dict] = None,
    pipeline_version: str = "v15_v2_director",  # DEFAULT: Use path with Content Completeness Validator
    generation_scope: str = "full",
    model: Optional[str] = None,
    video_provider: str = "ltx",
    job_update_callback: Optional[Callable[[Dict, bool], None]] = None
) -> Tuple[Dict, AnalyticsTracker]:
    """
    Execute the True Unified Pipeline (Single LLM Call).
    
    Flow:
    0. Image Processing (Save Datalab images)
    1. UnifiedContentGenerator -> V2 JSON (Single Call)
    2. Transform -> Player Schema
    3. GAP FILL 1: Manim Code Generation (Bridge)
    4. GAP FILL 2: TTS Generation
    5. Link Images & Renderers (Manim + WAN)
    """
    
    tracker = create_tracker(job_id)
    TRACKER_COLORS = "\033[94m" # Blue
    RESET_COLORS = "\033[0m"

    def log_status(phase: str, message: str):
        logger.info(f"[Job {job_id}] {phase}: {message}")
        print(f"{TRACKER_COLORS}[PIPELINE STATUS] {phase.upper()}: {message}{RESET_COLORS}")
        if update_status_callback:
            update_status_callback(job_id, phase, message)
                
    try:
        # User Request: Skip TTS in Dry Run
        if dry_run:
            logger.info("Pipeline: Dry Run active - Disabling TTS generation.")
            generate_tts = False

        if not markdown_content:
            raise PipelineUnifiedError("Markdown content is empty", "input_validation")

        # --- PHASE 0: Image Processing ---
        saved_images = {}
        images_list = "None"
        output_path = output_dir if output_dir else Path(f"jobs/{job_id}")
        output_path.mkdir(parents=True, exist_ok=True)
        
        if images_dict:
            log_status("image_processing", f"Processing {len(images_dict)} images...")
            images_dir = output_path / "images"
            try:
                saved_images = save_datalab_images(images_dict, str(images_dir), apply_green_screen=True)
                if saved_images:
                    images_list = ", ".join(saved_images.keys())
                    logger.info(f"Saved {len(saved_images)} images to {images_dir}")
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
                # Continue without images rather than failing pipeline
        else:
            # Try to extract refs from markdown (if already local)
            image_refs = extract_image_refs_from_markdown(markdown_content)
            if image_refs:
                images_list = ", ".join([ref['filename'] for ref in image_refs])
                logger.info(f"Found {len(image_refs)} image references in markdown")

        # --- PHASE 1: Unified Generation (Single Call) ---
        log_status("llm_generation", "Generating full presentation (Single Call)...")
        start_time = time.time()
        
        # 1. Generate (Retries handled internally)
        print(f"=" * 80)
        print(f"[PIPELINE DEBUG] pipeline_version received: '{pipeline_version}'")
        print(f"[PIPELINE DEBUG] Checking if == 'v15_v2_director': {pipeline_version == 'v15_v2_director'}")
        print(f"=" * 80)
        
        if pipeline_version == "v15_v2_director":
            print(f"[PIPELINE DEBUG] ✓ BRANCH: Director Mode (V2.5) - Calling generate_director_presentation")
            log_status("llm_generation", "Generating Director Mode presentation (Pointers)...")
            
            # ISS-207: Disable TTS for V2.5 pipelines as per user request
            if not dry_run: # Keep dry_run's own logic separate
                generate_tts = False
                logger.info("Pipeline: V2.5 Director Mode active - Disabling TTS generation (User Preference).")
            
            # Save source markdown for Player V2.5
            source_md_path = output_path / "source_markdown.md"
            with open(source_md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"Saved source markdown to {source_md_path}")
            
            # Save Smart Chunker output for Content Completeness Validator
            log_status("chunker", "Running Smart Chunker for validation ground truth...")
            from core.smart_chunker import call_smart_chunker
            
            artifacts_dir = output_path / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                chunker_output = call_smart_chunker(
                    markdown_content=markdown_content,
                    subject=subject,
                    tracker=tracker
                )
                
                chunker_path = artifacts_dir / "01_chunker.json"
                with open(chunker_path, "w", encoding="utf-8") as f:
                    json.dump(chunker_output, f, indent=2)
                
                logger.info(f"Saved chunker output to {chunker_path}")
            except Exception as e:
                logger.warning(f"Smart Chunker failed (non-critical for validation): {e}")
                # Continue without chunker output - validator will skip if not available

            # v2_output = generate_director_presentation(
            #     markdown_content=markdown_content,
            #     subject=subject,
            #     grade=grade,
            #     images_list=images_list,
            #     update_status_callback=log_status
            # )
            
            # Start LLM Phase
            llm_phase = tracker.start_phase("llm_generation", model=model or "default")
            
            # PHASE 7 SWAP: Use Partition & Conquer architecture
            config = GeneratorConfig(model=model) if model else None
            director = PartitionDirectorGenerator(config=config)
            v2_output = director.generate_presentation_partitioned(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                images_list=images_list,
                update_status_callback=log_status,
                generation_scope=generation_scope,
                output_dir=str(output_dir)
            )
            
            tracker.end_phase(
                phase_name="llm_generation",
                input_tokens=0, # TODO: Get from director output if available
                output_tokens=0
            )
            
            # Director output is already close to player schema, but needs standard metadata
            presentation = v2_output # It returns directly valid schema
            
            # Update metadata if not present or preserve chunk info
            if "metadata" not in presentation:
                presentation["metadata"] = {}
                
            # Enrich metadata
            inner_meta = v2_output.get("metadata", {})
            presentation["metadata"].update({
                "doc_length": len(markdown_content),
                "chunks": inner_meta.get("chunks", 1),
                "llm_calls": inner_meta.get("llm_calls", 1),
                "pipeline_mode": "v2.5-partition-conquer",
                "total_sections": len(presentation.get("sections", []))
            })
            
            presentation["avatar_global"] = {
                "style": "teacher",
                "default_position": "right",
                "default_width_percent": 52,
                "gesture_enabled": True
            }
            
            # --- PHASE 1.5: CONTENT COMPLETENESS VALIDATION (DISABLED BY USER REQUEST) ---
            # log_status("validation", "Validating content completeness...")
            
            # from core.validators.content_completeness_validator import validate_content_completeness
            # import time as time_module
            
            # Track validation timing for analytics
            # validation_start_time = time_module.time()
            
            # validation_result = validate_content_completeness(
            #     presentation=presentation,
            #     job_dir=str(output_path),
            #     source_markdown=markdown_content
            # )
            
            # validation_end_time = time_module.time()
            # validation_duration = validation_end_time - validation_start_time
            
            # Save validation report
            # validation_path = artifacts_dir / "completeness_validation.json"
            # with open(validation_path, "w", encoding="utf-8") as f:
            #     json.dump(validation_result, f, indent=2)
            
            # logger.info(f"Validation result: {validation_result['validation_status']}")
            
            # Track validator metrics in analytics
            # metrics = validation_result.get('metrics', {})
            # tracker.set_content_completeness_metrics(
            #     executed=True,
            #     validation_status=validation_result['validation_status'],
            #     execution_time=validation_duration,
            #     word_count_ratio=metrics.get('word_count_ratio', 0.0),
            #     topics_covered=metrics.get('topics_covered', 0),
            #     topics_total=metrics.get('topics_total', 0),
            #     images_referenced=metrics.get('images_referenced', 0),
            #     images_total=metrics.get('images_total', 0),
            #     retry_attempted=False,  # Will update if retry happens
            #     retry_success=False,
            #     missing_content=validation_result.get('missing_content_summary', ''),
            #     error=validation_result.get('error')
            # )
            
            # MOCK VALIDATION RESULT FOR DOWNSTREAM LOGIC
            validation_result = {"validation_status": "passed"}
            
            # Only retry if NOT in dry-run mode (retry requires LLM calls)
            # if validation_result["validation_status"] == "failed" and not dry_run:
                # log_status("validation", "Content validation FAILED - Retrying with enhanced prompt")
                
                # Get enhanced prompt with missing content details
                # retry_prompt = validation_result.get("retry_prompt_enhancement", "")
                
                # logger.warning(f"Validation failed. Retrying with prompt:\n{retry_prompt}")
                
                # Re-run Director with enhanced prompt
                # log_status("llm_generation", "Regenerating presentation with missing content details...")
                
                # v2_output_retry = director.generate_presentation_partitioned(
                #     markdown_content=markdown_content,
                #     subject=subject,
                #     grade=grade,
                #     images_list=images_list,
                #     update_status_callback=log_status,
                #     generation_scope=generation_scope,
                #     output_dir=str(output_dir),
                #     missing_content_hint=retry_prompt  # Inject missing content feedback
                # )
                
                # presentation = v2_output_retry
                
                # Update metadata after retry
                # if "metadata" not in presentation:
                #     presentation["metadata"] = {}
                # presentation["metadata"]["validation_retry"] = True
                
                # Validate again (only once - then fail hard if still incomplete)
                # retry_validation_start = time_module.time()
                # validation_result_retry = validate_content_completeness(
                #     presentation=presentation,
                #     job_dir=str(output_path),
                #     source_markdown=markdown_content
                # )
                # retry_validation_duration = time_module.time() - retry_validation_start
                
                # Save retry validation report
                # validation_retry_path = artifacts_dir / "completeness_validation_retry.json"
                # with open(validation_retry_path, "w", encoding="utf-8") as f:
                #     json.dump(validation_result_retry, f, indent=2)
                
                # Update analytics with retry metrics
                # retry_metrics = validation_result_retry.get('metrics', {})
                # tracker.set_content_completeness_metrics(
                #     executed=True,
                #     validation_status=validation_result_retry['validation_status'],
                #     execution_time=validation_duration + retry_validation_duration,  # Total time
                #     word_count_ratio=retry_metrics.get('word_count_ratio', 0.0),
                #     topics_covered=retry_metrics.get('topics_covered', 0),
                #     topics_total=retry_metrics.get('topics_total', 0),
                #     images_referenced=retry_metrics.get('images_referenced', 0),
                #     images_total=retry_metrics.get('images_total', 0),
                #     retry_attempted=True,
                #     retry_success=(validation_result_retry['validation_status'] == 'passed'),
                #     missing_content=validation_result_retry.get('missing_content_summary', ''),
                #     error=validation_result_retry.get('error')
                # )
                
                # if validation_result_retry["validation_status"] == "failed":
                #     error_msg = f"Content validation failed after retry. Missing content: {validation_result_retry}"
                #     logger.error(error_msg)
                #     raise PipelineUnifiedError(error_msg, "content_validation")
                # else:
                #     log_status("validation", "Content validation PASSED on retry ✓")
                #     presentation["metadata"]["validation_retry_success"] = True
            # elif validation_result["validation_status"] == "failed" and dry_run:
                # In dry-run mode, just log the failure but don't retry
                # log_status("validation", "Content validation FAILED (dry-run - no retry)")
                # logger.warning(f"Validation failed in dry-run mode: {validation_result}")
                # presentation["metadata"]["validation_failed_dry_run"] = True
            # else:
                # log_status("validation", "Content validation PASSED ✓")
                # presentation["metadata"]["validation_passed_first_attempt"] = True
            
        else:
            # Legacy V2 Unified
            print(f"[PIPELINE DEBUG] ✗ BRANCH: Legacy V2 Unified - Calling generate_presentation")
            v2_output = generate_presentation(
                markdown_content=markdown_content,
                subject=subject,
                grade=grade,
                images_list=images_list,
                output_dir=str(output_dir)
            )
            
            # 2. Transform to Player Schema
            presentation = transform_to_player_schema(
                v2_output,
                subject=subject,
                grade=grade
            )
        
        llm_duration = time.time() - start_time
        logger.info(f"Unified Generation took {llm_duration:.2f}s")
        
        # Track Layout Decisions
        tracker.track_decision(
            agent_name="UnifiedContentGenerator",
            decision_type="structure",
            options=["sections"],
            selected=f"{len(presentation.get('sections', []))} sections",
            reason=v2_output.get("decision_log", {}).get("content_analysis", "Review complete")
        )

        # --- PHASE 2: Validation & Policy ---
        log_status("validation", "Enforcing renderer policies...")
        presentation = enforce_renderer_policy(presentation)
        
        # --- PHASE 2.5: Duration Estimation (CRITICAL for Manim Timing) ---
        # ISS-FIX: Apply word-count estimates BEFORE Manim Codegen so validator has budgets.
        log_status("tts_estimation", "Calculating narration durations (Estimates)...")
        try:
            from core.tts_duration import _apply_estimates
            presentation = _apply_estimates(presentation)
            logger.info("Pipeline: Applied early duration estimates for validator budgets")
        except Exception as e:
            logger.warning(f"Early duration estimation failed: {e}")
        
        # --- PHASE 3: MANIM CODE BRIDGING (Crucial Step) ---
        # The Unified LLM outputs 'manim_spec' (text) but no code.
        # We must explicitly call ManimCodeGenerator to fill this gap.
        
        manim_gen = ManimCodeGenerator()
        sections = presentation.get("sections", [])
        manim_sections = []
        for i, section in enumerate(sections):
            # Safety: Skip if section is not a dict
            if not isinstance(section, dict):
                logger.warning(f"Section {i} is not a dict (type: {type(section)}), skipping...")
                continue
                
            # FIXED: Map derived_renderer (Director) to renderer (Executor)
            if "derived_renderer" in section and "renderer" not in section:
                section["renderer"] = section["derived_renderer"]
            
            renderer = section.get("renderer")
            # Only generate code if renderer is manim
            # AND we don't already have code (Unified LLM doesn't produce code, so this is always true)
            if renderer == "manim":
                manim_sections.append((i, section))

        if manim_sections:
            tracker.start_phase("manim_codegen", model="anthropic/claude-sonnet-4")
            log_status("manim_codegen", f"Parallelizing code generation for {len(manim_sections)} Manim sections...")
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                def process_manim(idx_sec):
                    idx, sec = idx_sec
                    try:
                        log_status("manim_codegen", f"Generating Manim code for Section {idx+1}: {sec.get('title')}...")
                        
                        # Transform V2.5 Director section to Manim Code Generator format
                        # The generator expects 'narration_segments' at top level, but Director has 'narration.segments'
                        nar = sec.get("narration", {})
                        segments = nar.get("segments", [])
                        
                        # Extract manim_spec from Director's segment_specs (V2.5 format)
                        # V2.5 Director puts manim_scene_spec at segment level, usually inside render_spec
                        segment_specs = sec.get("segment_specs", [])
                        if not segment_specs:
                            segment_specs = sec.get("render_spec", {}).get("segment_specs", [])
                        
                        manim_spec_from_director = None
                        
                        # Find first segment with manim renderer and extract its spec
                        for seg_spec in segment_specs:
                            if isinstance(seg_spec, dict) and seg_spec.get("renderer") == "manim":
                                manim_spec_from_director = seg_spec.get("manim_scene_spec", "")
                                if manim_spec_from_director:
                                    logger.info(f"[MANIM] Found manim_scene_spec in segment_specs: {len(manim_spec_from_director)} chars")
                                    break
                        
                        # Fallback: try render_spec (legacy format)
                        if not manim_spec_from_director:
                            render_spec = sec.get("render_spec", {})
                            manim_spec_from_director = render_spec.get("manim_scene_spec")
                            if isinstance(manim_spec_from_director, dict):
                                manim_spec_from_director = manim_spec_from_director.get("description", "")
                        
                        section_data_for_generator = {
                            "section_title": sec.get("title", "Section"),
                            "narration_segments": segments,  # Flatten the nested structure
                            "manim_spec": manim_spec_from_director or sec.get("explanation_plan", ""),
                            "visual_description": sec.get("visual_description", ""),
                            "formulas": [],
                            "key_terms": []
                        }
                        
                        print(f"[MANIM CODEGEN DEBUG] Section {idx+1} has {len(segments)} narration segments")
                        
                        res = manim_gen.generate_code(section_data=section_data_for_generator, style_config={"style": "standard"})
                        integrate_manim_code_into_section(sec, res)
                        tracker.add_llm_call(
                            phase="ManimCodeGenerator",
                            model="anthropic/claude-sonnet-4",
                            prompt_tokens=1000, # Placeholder, actual tokens would be dynamic
                            completion_tokens=1000 # Placeholder
                        )
                        return True
                    except Exception as e:
                        logger.error(f"Manim codegen failed for section {idx+1}: {e}")
                        return False

                results = list(executor.map(process_manim, manim_sections))
                manim_count = sum(1 for r in results if r)
                log_status("manim_codegen", f"Generated code for {manim_count} Manim sections")
            tracker.end_phase("manim_codegen", 0, 0)

        # --- PHASE 3.5: Checkpoint Save ---
        if output_dir:
            pres_path = os.path.join(output_dir, "presentation.json")
            # V2.5 FIX: Use lock to prevent race with avatar/TTS threads starting soon
            with presentation_lock:
                with open(pres_path, "w", encoding="utf-8") as f:
                    json.dump(presentation, f, indent=4)
            logger.info(f"Pipeline: Saved presentation checkpoint to {pres_path}")
            
            # NEW: Mark blueprint as ready for frontend
            log_status("blueprint_ready", "Blueprint (presentation.json) is Ready! You can view the Player now.")
            if job_update_callback:
                job_update_callback({
                    "blueprint_ready": True,  # NEW FIELD
                    "status": "processing",
                    "current_step_name": "Blueprint Ready - Rendering Assets...",
                    "current_phase_key": "rendering"
                }, persist=True)

        # --- PHASE 4: AUTOMATED PARALLEL FORK (Avatar + TTS + Manim/WAN) ---
        # 4a. Trigger Avatar Generation (Fire-and-Forget)
        # 4a. Trigger Avatar Generation (Fire-and-Forget)
        # 4a. Trigger Avatar Generation 
        # MOVED TO API/APP.PY to correct concurrency and status handling issues.
        log_status("avatar_generation", "Avatar generation delegated to Job Manager (Async)")
        
        # --- PHASE 4b: TTS Audio Generation (Background) ---
        # Step 1: Skip estimates (already applied in Phase 2.5)
        
        # Step 2: Fire off TTS audio generation in background (LOW PRIORITY - doesn't block)
        tts_thread = None
        if output_dir and generate_tts:
            log_status("tts_generation", "Starting TTS audio generation (background)...")
            
            from threading import Thread
            import copy
            
            def run_tts_background(pres_copy, out_dir, provider, job_id_ref):
                """Background TTS generation - runs while rendering proceeds."""
                try:
                    from core.tts_duration import update_durations_simplified
                    logger.info(f"[TTS-BG] Starting background TTS for job {job_id_ref}")
                    
                    # This will generate audio files but NOT block main thread
                    result_pres = update_durations_simplified(
                        pres_copy,
                        out_dir,
                        production_provider=provider,
                        update_status_callback=None  # No status updates from background
                    )
                    
                    # Save updated presentation with audio paths
                    # V2.5 FIX: Use lock to prevent race with avatar/WAN threads
                    pres_path = Path(out_dir) / "presentation.json"
                    with presentation_lock:
                        with open(pres_path, "w") as f:
                            json.dump(result_pres, f, indent=4)
                    logger.info(f"[TTS-BG] Background TTS complete for job {job_id_ref}")
                    
                except Exception as e:
                    logger.error(f"[TTS-BG] Background TTS failed: {e}")
            
            # Make a deep copy for the background thread
            pres_for_tts = copy.deepcopy(presentation)
            tts_thread = Thread(
                target=run_tts_background,
                args=(pres_for_tts, output_dir, tts_provider, job_id),
                daemon=True
            )
            tts_thread.start()
            log_status("tts_generation", "TTS audio generation running in background...")
        elif not generate_tts:
            log_status("tts_generation", "TTS disabled - using duration estimates only")

        
        # --- PHASE 5: Image Linking & Visual Rendering ---
        
        # Link Images (if any)
        if saved_images and output_dir:
            log_status("image_linking", "Linking extracted images to content...")
            try:
                _link_images_to_presentation(presentation, saved_images, str(output_dir / "images"))
            except Exception as e:
                logger.error(f"Image linking failed: {e}")
                presentation.setdefault("metadata", {})["job_status"] = "completed_with_errors"
                presentation["metadata"]["error_summary"] = f"Image Linking Warning: {str(e)}."

        # Visual Rendering (Manim + WAN)
        if output_dir:
            tracker.start_phase("visual_rendering", model="renderer")
            
            # --- PART A: BLOCKING MANIM RENDERING ---
            log_status("rendering", "Rendering Manim video content (Blocking)...")
            # Only render Manim topics here - this BLOCKS until done
            render_results = render_all_topics(
                presentation,
                str(output_dir / "videos"),
                dry_run=dry_run,
                skip_wan=skip_wan,
                output_dir_base=str(output_dir),
                renderer_filter="manim", # NEW: Only block for Manim
                video_provider=video_provider
            )
            
            logger.info(f"Manim Render results: {len(render_results)} videos processed")
            
            # ISS-FIX: Apply video paths from render results back to presentation sections!
            for result in render_results:
                section_id_result = result.get("topic_id")
                status = result.get("status")
                error = result.get("error")
                video_path = result.get("video_path")
                beat_videos = result.get("beat_videos", [])
                recap_video_paths = result.get("recap_video_paths", [])
                
                for section in presentation.get("sections", []):
                    if section.get("section_id") == section_id_result:
                        # Log detailed render status to analytics
                        retry_link = None
                        if status == "failed" or status == "compilation_failed":
                            # Construct retry URL for simple copy-paste or API trigger
                            retry_link = f"/retry_phase/{job_id}?phase=manim&section={section_id_result}"
                            
                        tracker.add_render_detail(
                            section_id=str(section_id_result),
                            section_type=section.get("section_type", "unknown"),
                            renderer=section.get("renderer", "unknown"),
                            duration=0.0, # detailed duration needs to be passed back from render_all_topics
                            status=status,
                            metadata={"error": error} if error else {},
                            retry_action=retry_link
                        )

                        # Capture render status for diagnostic visibility
                        if status == "failed" or status == "compilation_failed":
                            section["render_error"] = error
                            # Also add to global metadata for quick inspection
                            meta = presentation.setdefault("metadata", {})
                            meta.setdefault("render_errors", []).append({
                                "section_id": section_id_result,
                                "section_type": section.get("section_type"),
                                "error": error
                            })
                            meta["job_status"] = "completed_with_errors"

                        if video_path:

                            rel_path = os.path.basename(video_path)
                            section["video_path"] = f"videos/{rel_path}"
                        if beat_videos:
                            section["beat_videos"] = [f"videos/{Path(p).name}" for p in beat_videos]
                            # Also populate visual_beats[].video_asset for player sync
                            visual_beats = section.get("visual_beats", [])
                            for idx, beat_path in enumerate(beat_videos):
                                if idx < len(visual_beats):
                                    visual_beats[idx]["video_asset"] = f"videos/{Path(beat_path).name}"
                            section["visual_beats"] = visual_beats
                        if recap_video_paths:
                            # ISS-161/200: Ensure recap videos are properly linked for V2.5 sequencing
                            section["recap_video_paths"] = [f"videos/{Path(p).name}" for p in recap_video_paths]
                            # For recap, also set the first video as the main video_path for compatibility
                            if not section.get("video_path") and recap_video_paths:
                                section["video_path"] = f"videos/{Path(recap_video_paths[0]).name}"
                        break

            # --- PHASE 5.5: Final State Save (CRITICAL) ---
            # Must save BEFORE triggering async WAN job to avoid race condition where
            # main thread overwrites async thread's updates.
            if output_dir:
                pres_path = os.path.join(output_dir, "presentation.json")
                # V2.5 FIX: Use lock for thread-safe write before WAN thread starts
                with presentation_lock:
                    with open(pres_path, "w", encoding="utf-8") as f:
                        json.dump(presentation, f, indent=4)
                logger.info(f"Pipeline: Saved FINAL presentation to {pres_path}")
            
            # --- PART B: WAN RENDERING (Synchronous / Blocking) ---
            log_status("wan_rendering", "Starting WAN video generation (Blocking)...")
            try:
                from core.renderer_executor import submit_wan_background_job
                
                # Submit synchronously to hold the worker slot
                # This prevents "Thundering Herd" on GPU/WAN APIs
                try:
                    submit_wan_background_job(
                        presentation, 
                        str(output_dir / "videos"), 
                        job_id, 
                        skip_wan, 
                        skip_avatar, 
                        video_provider
                    )
                except TypeError as te:
                    if "positional arguments" in str(te):
                        logger.warning(f"Pipeline: Detected legacy submit_wan_background_job signature. Retrying with 5 args. Error: {te}")
                        submit_wan_background_job(
                            presentation, 
                            str(output_dir / "videos"), 
                            job_id, 
                            skip_wan, 
                            skip_avatar
                        )
                    else:
                        raise te
                        
                logger.info(f"Pipeline: Completed synchronous WAN generation for job {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to execute WAN generation: {e}")
            
            tracker.end_phase("visual_rendering", 0, 0)

        # --- PHASE 5.6: SAVE COMPREHENSIVE ANALYTICS ---
        if output_dir:
            try:
                # End pipeline tracking
                tracker.end_pipeline(status="completed")
                
                # Calculate content metrics from presentation
                sections = presentation.get("sections", [])
                total_segments = sum(
                    len(sec.get("narration", {}).get("segments", [])) 
                    for sec in sections
                )
                section_types = {}
                manim_count = 0
                video_count = 0
                static_count = 0
                manim_success = 0
                manim_failed = 0
                wan_success = 0
                wan_failed = 0
                quiz_question_count = 0
                flashcard_count = 0
                
                for sec in sections:
                    st = sec.get("section_type", "content")
                    section_types[st] = section_types.get(st, 0) + 1
                    renderer = sec.get("renderer", sec.get("derived_renderer", "none"))
                    
                    if renderer == "manim":
                        manim_count += 1
                        if sec.get("video_path") or sec.get("beat_videos"):
                            manim_success += 1
                        elif sec.get("render_error"):
                            manim_failed += 1
                    elif renderer in ("wan", "wan_video", "video"):
                        video_count += 1
                        if sec.get("video_path"):
                            wan_success += 1
                        elif sec.get("render_error"):
                            wan_failed += 1
                    else:
                        static_count += 1
                    
                    # Count quiz questions
                    if st == "quiz":
                        questions = sec.get("quiz_data", {}).get("questions", [])
                        if not questions:
                            questions = sec.get("questions", [])
                        quiz_question_count += len(questions)
                    
                    # Count flashcards
                    if st == "memory":
                        cards = sec.get("flashcards", [])
                        flashcard_count += len(cards)
                
                # Count audio files
                audio_dir = Path(output_dir) / "audio"
                audio_generated = 0
                if audio_dir.exists():
                    audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))
                    audio_generated = len([f for f in audio_files if f.stat().st_size > 1000])
                
                # Count video files
                video_dir = Path(output_dir) / "videos"
                video_generated = 0
                if video_dir.exists():
                    video_files = list(video_dir.glob("*.mp4"))
                    video_generated = len([f for f in video_files if f.stat().st_size > 5000])
                
                # Get avatar status
                avatar_success = 0
                avatar_failed = 0
                avatar_status_path = Path(output_dir) / "avatar_status.json"
                if avatar_status_path.exists():
                    try:
                        with open(avatar_status_path, "r") as f:
                            avatar_status = json.load(f)
                        # Parse message like "Sequential processing complete. Success: 5, Failed: 8"
                        msg = avatar_status.get("message", "")
                        import re
                        match = re.search(r"Success:\s*(\d+).*Failed:\s*(\d+)", msg)
                        if match:
                            avatar_success = int(match.group(1))
                            avatar_failed = int(match.group(2))
                    except Exception:
                        pass
                
                # Set content metrics
                tracker.set_content_metrics(
                    total_sections=len(sections),
                    total_segments=total_segments,
                    total_slides=len(sections),
                    section_types=section_types,
                    qa_pair_count=quiz_question_count
                )
                tracker.set_renderer_metrics(
                    manim_videos=manim_count,
                    wan_videos=video_count,
                    static_slides=static_count,
                    failed_renders=manim_failed + wan_failed
                )
                
                # Set comprehensive validation metrics
                tracker.set_validation_metrics(
                    section_types=section_types,
                    quiz_question_count=quiz_question_count,
                    flashcard_count=flashcard_count,
                    audio_generated=audio_generated,
                    audio_expected=len(sections) if generate_tts else 0,
                    video_generated=video_generated,
                    video_expected=manim_count + video_count,
                    manim_success=manim_success,
                    manim_failed=manim_failed,
                    wan_success=wan_success,
                    wan_failed=wan_failed,
                    avatar_success=avatar_success,
                    avatar_failed=avatar_failed
                )
                
                # Save to analytics.json
                analytics_path = Path(output_dir) / "analytics.json"
                tracker.save_to_file(str(analytics_path))
                log_status("analytics", f"Analytics saved - Quality Score: {tracker.analytics.validation.quality_score}/100")
                
            except Exception as e:
                logger.warning(f"Failed to save analytics: {e}")
                import traceback
                logger.warning(traceback.format_exc())


        # --- PHASE 6: AUTOMATED CERTIFICATION ---
        if output_dir:
            try:
                cert_summary = JobCertifier.certify_job(str(output_dir))
                log_status("certification", f"Job Validation: {cert_summary}")
            except Exception as e:
                logger.error(f"Certification Phase Failed (Non-Critical): {e}")
                log_status("certification", f"Certification Warning: Report generation failed, but job is valid.")
                presentation.setdefault("metadata", {})["job_status"] = "completed_with_errors"
                presentation["metadata"]["error_summary"] = f"Certification Warning: {str(e)}."


        return presentation, tracker

    except Exception as e:
        import traceback
        logger.error(f"Unified Pipeline Failed: {e}\n{traceback.format_exc()}")
        raise PipelineUnifiedError(str(e), "unknown")


def _link_images_to_presentation(presentation: dict, saved_images: dict, images_dir: str) -> None:
    """Link extracted images to visual_content in presentation segments."""
    from pathlib import Path
    
    # Build a lookup by image filename (normalized)
    image_lookup = {}
    for orig_name, saved_info in saved_images.items():
        if isinstance(saved_info, dict):
            # If saved_info is dict {filename: ..., path: ...}
            filename = saved_info.get('filename', orig_name)
        else:
            # If saved_info is just path string
            filename = Path(saved_info).name if saved_info else orig_name
            
        image_lookup[orig_name.lower()] = filename
        image_lookup[filename.lower()] = filename
    
    for section in presentation.get("sections", []):
        # Link to visual_beats (legacy)
        for beat in section.get("visual_beats", []):
            # Check if this beat references an image
            if beat.get("visual_type") == "image":
                desc = beat.get("description", "").lower()
                
                # Check for direct match in description
                found_match = None
                for key, fname in image_lookup.items():
                    if key in desc or fname.lower() in desc:
                        found_match = fname
                        break
                
                if found_match:
                    beat["image_asset"] = f"images/{found_match}"
        
        # ISS-FIX: Link to segments' visual_content (for player to display)
        for seg in section.get("narration", {}).get("segments", []):
            vc = seg.get("visual_content", {})
            if not isinstance(vc, dict):
                continue
            
            # Check for image_id reference from LLM
            image_id = vc.get("image_id")
            content_type = vc.get("content_type", "")
            
            if image_id or content_type in ("image", "diagram"):
                # Try to find matching image
                found_match = None
                
                # First try image_id directly
                if image_id:
                    normalized_id = image_id.lower()
                    for key, fname in image_lookup.items():
                        if normalized_id in key or key in normalized_id:
                            found_match = fname
                            break
                
                # Fallback: try verbatim_content as description
                if not found_match and vc.get("verbatim_content"):
                    desc = vc.get("verbatim_content", "").lower()
                    for key, fname in image_lookup.items():
                        if key in desc or fname.lower() in desc:
                            found_match = fname
                            break
                
                if found_match:
                    vc["image_path"] = f"images/{found_match}"
                    seg["visual_content"] = vc  # Update in place
