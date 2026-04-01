import os
import logging
import asyncio
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict
from core.unified_content_generator import (
    GeneratorConfig,
    extract_json_from_response,
    call_openrouter_llm,
    normalize_output,
)
from core.utils.smart_partitioner import SmartPartitioner
from core.tts_duration import update_durations_simplified

logger = logging.getLogger(__name__)


def inject_missing_image_ids(
    sections: List[Dict], images_list: str, source_content: str
) -> int:
    """
    Pipeline-level fix: Scan visual_beats for diagram/image types with null image_id
    and inject the correct image_id based on markdown_pointer matching.

    Returns: Number of image_ids injected
    """
    injected_count = 0

    # Parse images_list (could be JSON string, comma-separated string, or list)
    available_images = []
    if images_list and images_list != "None":
        if isinstance(images_list, list):
            available_images = images_list
        elif isinstance(images_list, dict):
            available_images = images_list
        elif isinstance(images_list, str):
            # Try JSON first
            try:
                available_images = json.loads(images_list)
            except json.JSONDecodeError:
                # Fallback: Comma-separated string of filenames
                available_images = [
                    img.strip() for img in images_list.split(",") if img.strip()
                ]
                logger.info(
                    f"[ImageInjection] Parsed {len(available_images)} images from comma-separated string"
                )

    if not available_images:
        logger.info("[ImageInjection] No images available to inject")
        return 0

    # Extract image references from source markdown: ![alt](filename.jpg)
    image_refs_in_source = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", source_content)
    # Create map: {filename: alt_text, ...}
    source_image_map = {ref[1]: ref[0] for ref in image_refs_in_source}

    logger.info(
        f"[ImageInjection] Found {len(source_image_map)} image refs in source, {len(available_images)} available images"
    )

    for section in sections:
        visual_beats = section.get("visual_beats", [])
        for beat in visual_beats:
            visual_type = beat.get("visual_type", "")
            image_id = beat.get("image_id")

            # Only process diagram/image types with no image_id
            if visual_type in ["diagram", "image"] and not image_id:
                # Try to match based on markdown_pointer
                pointer = beat.get("markdown_pointer", {})
                start_phrase = pointer.get("start_phrase", "")

                # Strategy 1: Check if start_phrase contains an image reference
                matched_image = None
                for img_filename in source_image_map.keys():
                    if img_filename in start_phrase:
                        matched_image = img_filename
                        break

                # Strategy 2: Find image whose alt text matches pointer content
                if not matched_image:
                    for img_filename, alt_text in source_image_map.items():
                        if (
                            alt_text and len(alt_text) > 10
                        ):  # Skip empty/short alt texts
                            # Check if alt text keywords appear in source near pointer
                            if any(
                                word.lower() in start_phrase.lower()
                                for word in alt_text.split()[:3]
                            ):
                                matched_image = img_filename
                                break

                # Strategy 3: Check available_images list directly
                if not matched_image and isinstance(available_images, dict):
                    for key, info in available_images.items():
                        filename = (
                            info.get("filename", "")
                            if isinstance(info, dict)
                            else str(info)
                        )
                        alt = info.get("alt_text", "") if isinstance(info, dict) else ""
                        if alt and any(
                            word.lower() in start_phrase.lower()
                            for word in alt.split()[:3]
                        ):
                            matched_image = filename
                            break

                # Strategy 4: Proximity Check (Look for images near the pointer in source content)
                if not matched_image and source_content:
                    # Find start_phrase location
                    idx = source_content.find(start_phrase)
                    if idx != -1:
                        # Define scan window (e.g., +/- 500 chars)
                        window_start = max(0, idx - 500)
                        window_end = min(len(source_content), idx + 1000)
                        window_text = source_content[window_start:window_end]

                        # Find images in this window
                        nearby_images = re.findall(
                            r"!\[([^\]]*)\]\(([^)]+)\)", window_text
                        )
                        if nearby_images:
                            # Use the first found image in proximity
                            matched_image = nearby_images[0][1]
                            logger.info(
                                f"[ImageInjection] Strategy 4 (Proximity) found '{matched_image}' near pointer"
                            )

                # Strategy 5: Single Image Fallback (If only 1 image provided, use it!)
                if not matched_image:
                    # Check if available_images has exactly 1 entry
                    if (
                        isinstance(available_images, list)
                        and len(available_images) == 1
                    ):
                        # Check if this image looks like a diagram or relevant asset (simple heuristic)
                        matched_image = available_images[0]
                        logger.info(
                            f"[ImageInjection] Strategy 5 (Fallback) used single available image '{matched_image}'"
                        )
                    elif (
                        isinstance(available_images, dict)
                        and len(available_images) == 1
                    ):
                        key = list(available_images.keys())[0]
                        val = available_images[key]
                        matched_image = (
                            val.get("filename", str(val))
                            if isinstance(val, dict)
                            else str(val)
                        )
                        logger.info(
                            f"[ImageInjection] Strategy 5 (Fallback) used single available image '{matched_image}'"
                        )

                if matched_image:
                    # Safety net: normalize .jpg/.jpeg → .png (files always saved as .png)
                    matched_image = matched_image.replace(".jpeg", ".png").replace(
                        ".jpg", ".png"
                    )
                    beat["image_id"] = matched_image
                    injected_count += 1
                    logger.info(
                        f"[ImageInjection] Injected image_id '{matched_image}' for beat {beat.get('beat_id')}"
                    )
                else:
                    logger.warning(
                        f"[ImageInjection] Could not find matching image for beat {beat.get('beat_id')} (visual_type={visual_type})"
                    )

    logger.info(f"[ImageInjection] Total injected: {injected_count} image_ids")
    return injected_count


class PartitionDirectorGenerator:
    """
    Phase 7 Architecture: "Partition & Conquer".
    1. Physically partitions MD into chunks.
    2. Runs Global Worker on Full Doc.
    3. Runs Parallel Topic Workers on Chunks (Context + Target).
    """

    def __init__(
        self,
        config: Optional[GeneratorConfig] = None,
        content_prompt_file: Optional[str] = None,
        global_prompt_file: Optional[str] = None,
    ):
        self.config = config or GeneratorConfig()
        self.partitioner = SmartPartitioner(self.config)
        self.content_prompt_file = (
            content_prompt_file or "core/prompts/director_v3_partition_prompt.txt"
        )
        self.global_prompt_file = (
            global_prompt_file or "core/prompts/director_global_prompt.txt"
        )

        # Load Prompts (We will use inline prompts or load from file if complex)
        self.global_system = "You are the Global Director. Output JSON with Intro, Summary, Memory, Recap, Quiz."
        self.content_system = (
            "You are the Content Director. Visualize the TARGET TEXT using the Context."
        )

    async def generate_presentation_parallel__REMOVED_ASYNC(self):
        pass

    def generate_presentation_partitioned(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None,
        generation_scope: str = "full",  # New: "full", "global", "content"
        output_dir: Optional[str] = None,
        missing_content_hint: Optional[str] = None,  # NEW: For validation retry
    ) -> dict:
        # A. PARTITIONING (Skip if global-only)
        chunks = []
        if generation_scope in ["full", "content"]:
            if generation_scope == "content":
                # Treat the whole input as one single chunk (Manual Mode)
                chunks = [{"title": "Target Content", "content": markdown_content}]
                logger.info("Manual Scope: Treating input as a single target chunk.")
            else:
                msg = "Phase 1: Intelligent Partitioning..."
                logger.info(msg)
                if update_status_callback:
                    update_status_callback("partitioning", msg)
                chunks = self.partitioner.partition_markdown(
                    markdown_content, subject, grade
                )
                logger.info(f"Partitioned into {len(chunks)} physical chunks.")

        # B & C: PARALLEL EXECUTION (Global + Content)
        global_results = {}
        content_results = []

        msg = f"Phase 2 & 3: Generating Global and {len(chunks)} Content Chunks in Parallel..."
        logger.info(msg)
        if update_status_callback:
            update_status_callback("llm_generation", msg)

        max_workers = min(len(chunks) + 1, 12)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 1. Submit Global Worker (if needed)
            global_future = None
            if generation_scope in ["full", "global"]:
                global_future = executor.submit(
                    self._run_global_worker,
                    markdown_content,
                    subject,
                    grade,
                    output_dir,
                    missing_content_hint,
                )

            # 2. Submit Content Workers (if needed)
            future_to_index = {}
            if generation_scope in ["full", "content"]:
                for i, chunk in enumerate(chunks):
                    f = executor.submit(
                        self._run_content_worker_sync,
                        i,
                        chunk,
                        markdown_content if generation_scope == "full" else "",
                        subject,
                        grade,
                        images_list,
                        output_dir,
                    )
                    future_to_index[f] = i

                content_results = [None] * len(chunks)

            # 3. Collect Results
            if global_future:
                global_results = global_future.result()
                if not global_results:
                    raise RuntimeError("Global Worker failed to return a valid result.")

            if future_to_index:
                for future in as_completed(future_to_index):
                    i = future_to_index[future]
                    # This will raise if the worker thread raised
                    content_results[i] = future.result()
                    if not content_results[i]:
                        raise RuntimeError(
                            f"Content Worker for Chunk {i} failed to return a valid result."
                        )

        # D. STITCHING
        msg = "Phase 4: Stitching Presentation..."
        logger.info(msg)

        final_presentation = {
            "presentation_title": global_results.get(
                "presentation_title", f"{subject} Lesson"
            ),
            "sections": [],
            "metadata": {
                "generated_by": "v2.5-partition-director",
                "doc_length": len(markdown_content),
                "chunks": len(chunks),
                "llm_calls": 1
                + len(chunks)
                + (1 if generation_scope in ["full", "global"] else 0),
                "generation_scope": generation_scope,
            },
        }

        # 1. Intro
        if global_results.get("intro"):
            intro = global_results["intro"]
            intro["section_id"] = 1
            final_presentation["sections"].append(intro)

        # 2. Summary (V2.5 Bible: Summary comes BEFORE Content)
        if global_results.get("summary"):
            summary = global_results["summary"]
            summary["section_id"] = len(final_presentation["sections"]) + 1
            final_presentation["sections"].append(summary)

        # 3. Content Sections (Order matters - logic preserves chunk order)
        current_id = len(final_presentation["sections"]) + 1
        for chunk_res in content_results:
            if chunk_res:
                for sec in chunk_res:
                    sec["section_id"] = current_id
                    current_id += 1
                    # Ensure visual_beats is not empty for player compatibility
                    if not sec.get("visual_beats"):
                        sec["visual_beats"] = []

                    # SYNC SPLITTER (V2.5 Fix: Apply after global section_id is assigned)
                    if sec.get("renderer") in ["video", "wan_video", "wan"]:
                        self._apply_sync_splitter(sec)
                final_presentation["sections"].extend(chunk_res)

        # 3.5 IMAGE INJECTION FIX (Pipeline-level)
        # Scan for visual_type=diagram/image with null image_id and inject correct references
        content_sections = [
            s
            for s in final_presentation["sections"]
            if s.get("section_type") in ["content", "example"]
        ]
        if content_sections:
            injected = inject_missing_image_ids(
                content_sections, images_list, markdown_content
            )
            if injected > 0:
                msg = f"Phase 4.5: Injected {injected} missing image_ids"
                logger.info(msg)
                if update_status_callback:
                    update_status_callback("image_injection", msg)

        # 4. Memory, Memory Infographic, and Recap (Global Footer)
        for key in ["memory", "memory_infographic", "recap"]:
            if global_results.get(key):
                sec = global_results[key]
                sec["section_id"] = current_id
                current_id += 1

                # SYNC SPLITTER (V2.5 Fix: Apply after global section_id is assigned)
                if sec.get("renderer") in ["video", "wan_video", "wan"]:
                    self._apply_sync_splitter(sec)

                final_presentation["sections"].append(sec)

        return final_presentation

    def _run_global_worker(
        self,
        full_md,
        subject,
        grade,
        output_dir: Optional[str] = None,
        missing_content_hint: Optional[str] = None,
    ) -> dict:
        """Generates Intro, Summary, Memory, Recap ONLY."""
        # Use existing 'director_global_prompt.txt' if available, or inline.
        # Strict Load of Global Prompt
        with open(self.global_prompt_file, "r", encoding="utf-8") as f:
            sys_p = f.read()

        # Inject validation feedback if retrying
        if missing_content_hint:
            sys_p += f"\n\n{missing_content_hint}\n"

        usr_p = f"Subject: {subject}\nGrade: {grade}\nCONTENT:\n{full_md}"  # Full context - let the LLM see everything
        from core.validators.v25_validator import V25Validator

        retries = 0
        max_retries = 3
        current_prompt = usr_p

        while retries < max_retries:
            try:
                r, _ = call_openrouter_llm(sys_p, current_prompt, self.config)
                data = extract_json_from_response(r)

                # VALIDATION GATE (GLOBAL)
                # print(f"\n[PHASE 1 DEBUG] Global Worker Response ({subject}, {grade}):")
                # print(json.dumps(data, indent=2))
                # print(f"[PHASE 1 DEBUG] --------------------------------------------------\n")

                # USER REQUEST: Save global debug dump
                if output_dir:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        debug_path = os.path.join(
                            output_dir, "debug_global_worker.json"
                        )
                        with open(debug_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        logger.info(f"Saved global worker debug to {debug_path}")
                    except Exception as e:
                        logger.warning(f"Failed to save global debug: {e}")

                errors = V25Validator.validate_global_response(data)

                if not errors:
                    # Map section IDs and apply splitter
                    for key in ["intro", "summary", "memory", "recap", "quiz"]:
                        if key in data:
                            sec = data[key]
                            # V3: Ensure Recap uses image_to_video renderer with render_spec
                            if key == "recap":
                                sec["renderer"] = "image_to_video"
                                # Always force-correct the render_spec for recap
                                rs = sec.get("render_spec", {})
                                rs["renderer"] = (
                                    "image_to_video"  # force even if LLM set text_to_video
                                )

                                # Convert video_prompts -> image_to_video_beats if needed
                                if not rs.get("image_to_video_beats"):
                                    video_prompts = rs.get("video_prompts", [])
                                    segs = sec.get("narration", {}).get("segments", [])
                                    if video_prompts:
                                        beats = []
                                        for i, vp in enumerate(video_prompts):
                                            prompt_text = (
                                                vp
                                                if isinstance(vp, str)
                                                else vp.get(
                                                    "prompt", "Cinematic recap scene."
                                                )
                                            )
                                            beats.append(
                                                {
                                                    "beat_id": f"recap_beat_{i + 1}",
                                                    "image_prompt_start": f"Cinematic recap opening frame {i + 1}. Photorealistic, vivid Indian setting, warm lighting, 16:9.",
                                                    "image_prompt_end": f"Cinematic recap closing frame {i + 1}. Photorealistic, vivid Indian setting, warm lighting, 16:9.",
                                                    "video_prompt": prompt_text,
                                                    "duration": 15,
                                                }
                                            )
                                        rs["image_to_video_beats"] = beats
                                        rs.pop("video_prompts", None)
                                    elif segs:
                                        beats = []
                                        for i, seg in enumerate(segs):
                                            beats.append(
                                                {
                                                    "beat_id": f"recap_beat_{i + 1}",
                                                    "image_prompt_start": f"Cinematic recap opening frame {i + 1}. Photorealistic, vivid Indian setting, warm lighting, 16:9.",
                                                    "image_prompt_end": f"Cinematic recap closing frame {i + 1}. Photorealistic, vivid Indian setting, warm lighting, 16:9.",
                                                    "video_prompt": seg.get(
                                                        "text", "Cinematic recap scene."
                                                    ),
                                                    "duration": 15,
                                                }
                                            )
                                        rs["image_to_video_beats"] = beats
                                    else:
                                        rs["image_to_video_beats"] = [
                                            {
                                                "beat_id": "recap_fallback",
                                                "image_prompt_start": "Cinematic recap opening frame.",
                                                "image_prompt_end": "Cinematic recap closing frame.",
                                                "video_prompt": "Cinematic lesson recap summary.",
                                                "duration": 15,
                                            }
                                        ]

                                # Recalculate total_duration_seconds
                                beats = rs.get("image_to_video_beats", [])
                                rs["total_duration_seconds"] = sum(
                                    b.get("duration", 15) for b in beats
                                )
                                sec["render_spec"] = rs
                    return data

                # Validation Failed
                logger.warning(
                    f"Global Worker Validation Failed (Attempt {retries + 1}): {errors}"
                )

                # Feedback Loop
                error_msg = "\n- ".join(errors)
                current_prompt += (
                    f"\n\n[SYSTEM: PREVIOUS ATTEMPT REJECTED]\n"
                    f"Your previous JSON output was invalid for the following reasons:\n- {error_msg}\n"
                    f"Please FIX these errors and regenerate the JSON strictly following the schema."
                )
                retries += 1
            except Exception as e:
                logger.error(f"Global Worker Exception (Attempt {retries + 1}): {e}")
                retries += 1

        raise RuntimeError(
            f"Global Worker failed all {max_retries} validation attempts."
        )

    def _run_content_worker_sync(
        self,
        index,
        chunk,
        full_context,
        subject,
        grade,
        images_list,
        output_dir: Optional[str] = None,
    ):
        """
        Sync Worker for Content chunks (for ThreadPoolExecutor).
        """
        try:
            # Load specialized prompt
            # Load specialized prompt (STRICT LOADING - NO FALLBACK)
            with open(self.content_prompt_file, "r", encoding="utf-8") as f:
                sys_p = f.read()

            usr_p = (
                f"SUBJECT: {subject}\n"
                f"Target Chunk Title: {chunk.get('title')}\n\n"
                f"=== FULL DOCUMENT CONTEXT (Read Only) ===\n{full_context}\n\n"
                f"=== AVAILABLE IMAGES (Usage Mandatory if relevant) ===\n{json.dumps(images_list, indent=2)}\n\n"
                f"=== TARGET CHUNK (VISUALIZE THIS) ===\n{chunk.get('content')}\n\n"
                f"Instructions: Create slides for the TARGET CHUNK only. Use images from the list above."
            )

            # Run LLM (Sync) with Validation Retry Loop
            # NOTE: We use a lightweight structural check here (not V25Validator) because
            # V3 uses threejs_spec instead of manim_scene_spec/video_prompts. Using V25Validator
            # here would reject every valid V3 response. Full V3 validation is handled
            # non-fatally by v3_validator.py in pipeline_v3.py Phase 2.

            retries = 0
            max_retries = 3
            current_prompt = usr_p

            while retries < max_retries:
                try:
                    response, _ = call_openrouter_llm(
                        sys_p, current_prompt, self.config
                    )

                    # [DEBUG] Save Raw LLM Response
                    try:
                        debug_file = f"debug_llm_chunk_{index}_attempt_{retries}.txt"
                        if output_dir:
                            os.makedirs(output_dir, exist_ok=True)
                            debug_file = os.path.join(output_dir, debug_file)
                        with open(debug_file, "w", encoding="utf-8") as f:
                            f.write(response)
                        logger.info(f"Saved raw LLM response to {debug_file}")
                    except Exception as e:
                        logger.warning(f"Failed to save debug LLM response: {e}")

                    data = extract_json_from_response(response)

                    if data is None:
                        # CRITICAL: Prevent NoneType crash
                        msg = f"LLM returned invalid/None JSON. Raw length: {len(response) if response else 0}"
                        logger.error(msg)
                        raise RuntimeError(msg)

                    # Lightweight structural check (schema-agnostic):
                    # Just verify we got a sections list with at least one section that has a renderer.
                    # Full V3-specific validation runs later (pipeline_v3.py Phase 2, non-fatal).
                    sections_result = data.get("sections", [])

                    # If LLM returned a bare section dict instead of {sections: [...]}, wrap it
                    if not sections_result and data.get("section_type"):
                        sections_result = [data]

                    errors = []
                    if not sections_result:
                        errors.append("No sections returned from Content Worker.")
                    else:
                        for sec in sections_result:
                            if not sec.get("renderer"):
                                errors.append(
                                    f"Section '{sec.get('title', '?')}' is missing 'renderer' field."
                                )
                            if not sec.get("narration"):
                                errors.append(
                                    f"Section '{sec.get('title', '?')}' is missing 'narration' field."
                                )

                    if not errors:
                        # INJECT CONTENT FIDELITY (Restore source text)
                        if sections_result and chunk.get("content"):
                            sections_result[0]["content"] = chunk.get("content")
                        return sections_result

                    # Validation Failed — give feedback to LLM
                    logger.warning(
                        f"Worker {index} Structural Check Failed (Attempt {retries + 1}/{max_retries}): {errors}"
                    )
                    error_msg = "\n- ".join(errors)
                    current_prompt += (
                        f"\n\n[SYSTEM: PREVIOUS ATTEMPT REJECTED]\n"
                        f"Your previous JSON output was invalid for the following reasons:\n- {error_msg}\n"
                        f"Please FIX these errors and regenerate the JSON strictly following the schema."
                    )
                    retries += 1

                except Exception as e:
                    logger.error(
                        f"Worker {index} Exception (Attempt {retries + 1}): {e}"
                    )
                    retries += 1

            # If all retries fail, raise error to stop pipeline
            raise RuntimeError(
                f"Content Worker {index} failed all {max_retries} attempts."
            )

        except Exception as e:
            logger.error(f"Partition Worker {index} failed outer: {e}")
            raise  # Re-raise to trigger failure in ThreadPoolExecutor result

    def _apply_sync_splitter(self, section: dict):
        """
        V2.5 Sync Rule: Map SHOW segments to render specs.
        - Manim: 1 spec per segment (no 15s limit).
        - WAN: Multiple beats if segment > 15s.
        - Prioritizes 'segment_specs' array for 1-to-1 mapping.
        """
        if "narration" not in section or "segments" not in section["narration"]:
            return

        renderer = section.get("renderer")
        if renderer not in ["video", "manim"]:
            return

        render_spec = section.get("render_spec", {})
        segment_specs = render_spec.get("segment_specs", [])

        # Build segment_id -> spec map
        spec_map = {
            spec["segment_id"]: spec for spec in segment_specs if "segment_id" in spec
        }

        # Legacy fallbacks
        v_prompts = section.get("video_prompts", []) or render_spec.get(
            "video_prompts", []
        )
        manim_spec_legacy = render_spec.get("manim_scene_spec")

        final_video_prompts = []
        final_manim_specs = []  # Specific for manim renderer output

        for idx, seg in enumerate(section["narration"]["segments"]):
            seg_id = seg.get("segment_id") or f"seg_{idx + 1}"

            # GAP FIX: Verify if visuals are actually required
            # If visual_layer is 'hide' (Teach Segment), do NOT generate a video prompt (saves $ and fixes garbage)
            directives = seg.get("display_directives", {})
            if directives.get("visual_layer") == "hide":
                continue

            text = seg.get("text", "")
            duration = seg.get(
                "duration_seconds", 15
            )  # Should be updated by tts_duration

            # Map spec to segment
            spec = spec_map.get(seg_id)

            if renderer == "manim":
                # Manim: 1 spec per segment (no 15s limit)
                manim_code_spec = ""
                if spec:
                    manim_code_spec = spec.get("manim_scene_spec", "")
                else:
                    manim_code_spec = (
                        manim_spec_legacy or "Mathematical conceptual animation."
                    )

                final_manim_specs.append(
                    {
                        "segment_id": seg_id,
                        "duration_seconds": duration,
                        "manim_scene_spec": manim_code_spec,
                    }
                )
                # Link segment to its manim video (per-segment filename)
                seg["video_file"] = f"topic_{section.get('section_id')}_{seg_id}.mp4"

            else:  # video/wan
                # Check for explicit beats provided by LLM
                llm_beats = spec.get("beats", []) if spec else []

                if llm_beats:
                    # Use LLM-provided beats and ensure unique naming
                    beat_ids = []
                    section_prefix = f"topic_{section.get('section_id')}_"

                    for beat in llm_beats:
                        original_id = beat.get("beat_id", "")
                        # Ensure ID is unique by prepending section if not already present
                        # (Assume seg_id in beat_id might collide, so we enforce prefix)
                        if not original_id.startswith("topic_"):
                            beat["beat_id"] = f"{section_prefix}{original_id}"

                        beat["segment_id"] = seg_id
                        final_video_prompts.append(beat)
                        beat_ids.append(beat["beat_id"])

                    seg["beat_videos"] = beat_ids
                else:
                    # Auto-split if > 15s or no beats provided
                    video_prompt = ""
                    if spec:
                        video_prompt = spec.get("video_prompt", "")
                    elif v_prompts:
                        # Fallback to cycling through legacy prompts
                        base_obj = v_prompts[idx % len(v_prompts)]
                        video_prompt = (
                            base_obj.get("prompt", str(base_obj))
                            if isinstance(base_obj, dict)
                            else str(base_obj)
                        )
                    else:
                        video_prompt = "Cinematic educational visualization."

                    num_beats = max(1, int((duration + 1) // 15))  # Ceiling-ish
                    if duration > 15:
                        logger.info(
                            f"Sync Splitter (WAN): Auto-splitting segment {seg_id} ({duration}s) into {num_beats} beats"
                        )

                    beat_ids = []
                    for i in range(num_beats):
                        # V2.5 Fix: Unique Naming to prevent collisions between sections
                        beat_id = (
                            f"topic_{section.get('section_id')}_{seg_id}_beat_{i + 1}"
                        )
                        prefix = (
                            ""
                            if i == 0
                            else "Keeping the previous scene exactly the same, continue showing: "
                        )
                        suffix = (
                            f" (Part {i + 1} of {num_beats})" if num_beats > 1 else ""
                        )

                        final_video_prompts.append(
                            {
                                "beat_id": beat_id,
                                "segment_id": seg_id,
                                "prompt": prefix + video_prompt + suffix,
                                "duration_hint": min(15, duration / num_beats),
                            }
                        )
                        beat_ids.append(beat_id)
                    seg["beat_videos"] = beat_ids

        # Store for downstream processing
        section["video_prompts"] = final_video_prompts
        section["_manim_segment_specs"] = final_manim_specs
        logger.info(
            f"Sync Splitter ({renderer}): Generated {len(final_video_prompts)} WAN beats / {len(final_manim_specs)} Manim specs for section {section.get('section_id')}"
        )


def generate_director_presentation(
    markdown_content: str,
    subject: str = "Science",
    grade: str = "Grade 10",
    images_list: str = "None",
    config: Optional[GeneratorConfig] = None,
    update_status_callback=None,
) -> dict:
    """Entry point for pipeline integration."""
    generator = DirectorGenerator(config)
    # Revert to standard loop (Sync) until ThreadPool implemented in V2
    # partition_director_generator is the class above, DirectorGenerator is legacy
    # The pipeline calls generate_presentation_partitioned directly on PartitionDirectorGenerator instance
    # IF this function is intended to call PartitionDirectorGenerator:

    # Correction: The pipeline uses PartitionDirectorGenerator directly.
    # This helper function seems to be for DirectorGenerator (legacy/loop).
    # Since we are modifying PartitionDirectorGenerator in this file, we don't need to change this function
    # unless it's used by the pipeline.

    # Wait, the pipeline calls `generate_presentation_partitioned` directly if using partition mode.
    # If using 'director' mode (legacy), it calls this.
    # Let's leave this as is (sync loop) or upgrade it if needed.
    # For now, we are fixing PartitionDirectorGenerator.generate_presentation_partitioned.

    return generator.generate_presentation_loop(
        markdown_content, subject, grade, images_list, update_status_callback
    )
