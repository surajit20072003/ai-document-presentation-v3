"""
V2.5 Unified Director Generator
Implements the "Director-Pointer" architecture.
Inherits from UnifiedContentGenerator but overrides validation and schema transformation.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from core.unified_content_generator import (
    GeneratorConfig,
    normalize_output,
    extract_json_from_response,
    call_openrouter_llm,
)
from core.utils.markdown_chunker import smart_split

logger = logging.getLogger(__name__)


# Load Prompts
def get_prompts():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(
        os.path.join(base, "prompts", "director_system_prompt.txt"),
        "r",
        encoding="utf-8",
    ) as f:
        director_system = f.read()
    with open(
        os.path.join(base, "prompts", "director_user_prompt.txt"), "r", encoding="utf-8"
    ) as f:
        director_user = f.read()
    with open(
        os.path.join(base, "prompts", "planner_system_prompt.txt"),
        "r",
        encoding="utf-8",
    ) as f:
        planner_system = f.read()
    with open(
        os.path.join(base, "prompts", "planner_bone_prompt.txt"), "r", encoding="utf-8"
    ) as f:
        planner_bone_system = f.read()
    with open(
        os.path.join(base, "prompts", "director_global_prompt.txt"),
        "r",
        encoding="utf-8",
    ) as f:
        director_global = f.read()
    return (
        director_system,
        director_user,
        planner_system,
        planner_bone_system,
        director_global,
    )


class DirectorGenerator:
    """
    Stand-alone generator class for V2.5 Director Mode.
    We don't strictly inherit because we want clean separation of logic.
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()

    def generate_presentation(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        topic_heading: str = None,
        system_prompt: str = None,
    ) -> dict:
        """
        Inner Director Loop: Generate sections for a specific topic chunk.
        Uses specialized prompts if provided.
        """
        # 1. Prepare Prompts
        director_system = system_prompt
        director_user = None

        if not director_system:
            # Fallback to default load
            director_system, director_user_template, _, _, _ = get_prompts()
            director_user = director_user_template

        if not director_user:
            # Load user prompt template if we only passed system prompt (case for specialized topic prompt)
            _, director_user_template, _, _, _ = get_prompts()
            director_user = director_user_template

        user_prompt = director_user.format(
            subject=subject,
            grade=grade,
            images_list=images_list,
            markdown_content=markdown_content,
        )

        logger.info("DirectorGenerator: Starting LLM call...")

        # reuse existing retry logic via function call if possible,
        # or implement simple retry here since we are using functional core
        # For simple integration, we'll mimic the retry loop from unified_content_generator

        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                # 1. Call LLM
                response, usage = call_openrouter_llm(
                    director_system, user_prompt, self.config
                )

                # 2. Extract JSON
                data = extract_json_from_response(response)

                # 3. Normalize
                data = normalize_output(data)

                # 4. Validate (New Director Schema) - NON-BLOCKING
                is_valid, errors = self.validate_director_schema(data, markdown_content)
                if not is_valid:
                    logger.warning(f"⚠️ Pointer validation warnings: {errors}")
                    logger.warning(
                        "Proceeding anyway - Player will handle resolution at runtime"
                    )
                    # Don't fail - let the job complete

                logger.info(f"DirectorGenerator: Success (Attempt {attempt + 1})")
                data["_llm_usage"] = usage
                data["spec_version"] = "v1.5-v2.5-director"
                return data

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                # Backoff logic is in lower layers usually, but here we just continue

        raise last_error

    def generate_presentation_loop(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None,
    ) -> dict:
        """
        Main entry point for V2.5 Director Planner-Executor Loop.
        1. Pass 1: Planner creates blueprint and logical chunks.
        2. Pass 2: Director executes each logical chunk in a loop.
        3. Merges results into final presentation.
        """
        director_sys, director_usr, planner_sys, _, _ = get_prompts()

        # --- PASS 1: THE PLANNER ---
        msg = "Phase 1: Generating Lesson Blueprint..."
        logger.info(f"DirectorGenerator: {msg}")
        if update_status_callback:
            update_status_callback("llm_generation", msg)

        planner_user = f"Subject: {subject}\nGrade: {grade}\n\nDOCUMENT CONTENT:\n{markdown_content}"

        try:
            planner_response, planner_usage = call_openrouter_llm(
                planner_sys, planner_user, self.config
            )
            blueprint = extract_json_from_response(planner_response)
        except Exception as e:
            logger.error(f"Planner failed: {e}. Falling back to blind chunking.")
            # Fallback to character-based chunking if planner fails
            return self._legacy_blind_loop(
                markdown_content, subject, grade, images_list, update_status_callback
            )

        plan = blueprint.get("logical_plan", [])
        globals = blueprint.get("global_sections", {})

        logger.info(
            f"DirectorGenerator: Planner identified {len(plan)} logical topics."
        )

        final_presentation = {
            "presentation_title": blueprint.get(
                "presentation_title", "Educational Presentation"
            ),
            "sections": [],
            "metadata": {
                "generated_by": "v1.5-v2.5-director",
                "total_topics": len(plan),
                "planner_id": "v2.5-pro-planner",
            },
        }

        # --- PASS 2: THE DIRECTOR LOOP ---
        total_usage = planner_usage

        # A. Add Intro (from Blueprint)
        intro_text = globals.get("intro", {}).get("text", "Welcome to the lesson.")
        final_presentation["sections"].append(
            {
                "section_type": "intro",
                "title": "Introduction",
                "renderer": "none",
                "narration": {
                    "segments": [{"segment_id": "intro_1", "text": intro_text}]
                },
            }
        )

        # B. Loop through Topics
        for i, topic in enumerate(plan):
            title = topic.get("topic_heading", f"Topic {i + 1}")
            msg = f"Phase 2: Directing Topic {i + 1}/{len(plan)}: {title}"
            logger.info(f"DirectorGenerator: {msg}")
            if update_status_callback:
                update_status_callback("llm_generation", msg)

            # Extract partial markdown for this topic
            start_p = topic.get("start_phrase", "")
            end_p = topic.get("end_phrase", "")

            # Smart extraction: Find positions in source
            topic_md = self._extract_topic_markdown(markdown_content, start_p, end_p)

            try:
                topic_data = self.generate_presentation(
                    topic_md, subject, grade, images_list, topic_heading=title
                )

                # Merge sections
                new_sections = topic_data.get("sections", [])
                for sec in new_sections:
                    # Filter out any duplicated intros/summaries the Director might have hallucinated
                    if (
                        sec.get("section_type") in ["intro", "summary", "recap"]
                        and i > 0
                    ):
                        continue
                    final_presentation["sections"].append(sec)

                # Accumulate usage
                usage = topic_data.get("_llm_usage", {})
                for k in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                    total_usage[k] = total_usage.get(k, 0) + usage.get(k, 0)

            except Exception as e:
                logger.error(f"Error in Topic {i + 1}: {e}")
                continue

        # C. Add Summary, Memory, Recap (from Blueprint)
        self._add_global_footer(final_presentation, globals, subject, grade)

        final_presentation["_llm_usage"] = total_usage
        return final_presentation

    def _extract_topic_markdown(self, full_md, start, end):
        """Extract markdown segment between two phrases."""
        if not start or not end:
            return full_md  # No fallback limit

        start_idx = full_md.find(start)
        end_idx = full_md.find(end)

        if start_idx != -1 and end_idx != -1:
            return full_md[start_idx : end_idx + len(end)]

        # If not found, return full text
        return full_md

    def _add_global_footer(
        self, presentation, globals, subject="Science", grade="Grade 10"
    ):
        """Add Summary, Memory, and Recap sections using LLM for high fidelity."""
        # V2.5: No more hardcoded strings. Use the Global Director!
        logger.info("[Director] Using LLM to generate high-fidelity Global sections.")

        _, _, _, _, global_system = get_prompts()

        # Prepare context for LLM
        # Use full presentation text if possible, or just the globals data
        summary_raw = globals.get("summary", {})
        memory_raw = globals.get("memory", [])
        recap_raw = globals.get("recap", [])

        global_context = {
            "presentation_title": presentation.get("presentation_title", "Lesson"),
            "summary_points": summary_raw.get("bullets", []),
            "memory_flashcards": memory_raw,
            "recap_scenes": recap_raw,
        }

        user_prompt = f"Subject: {subject}\nGrade: {grade}\n\nDATA:\n{json.dumps(global_context, indent=2)}"

        try:
            response, _ = call_openrouter_llm(global_system, user_prompt, self.config)
            data = extract_json_from_response(response)
            data = normalize_output(data)

            # Map LLM sections to presentation
            for key in ["summary", "memory", "recap", "quiz"]:
                if key in data:
                    sec = data[key]
                    # Ensure section_id is unique
                    sec["section_id"] = f"{key}_global"

                    # WAN SYNC SPLITTER: Check if WAN recap needs splitting (though usually small)
                    if key == "recap" and sec.get("renderer") == "video":
                        self._apply_sync_splitter(sec)

                    presentation["sections"].append(sec)
        except Exception as e:
            logger.error(
                f"Failed to generate global footer via LLM: {e}. Falling back to basic structure."
            )
            # Last resort fallback if even LLM fails
            self._basic_global_footer_fallback(presentation, globals)

    def _apply_sync_splitter(self, section):
        """
        V2.5 Sync Logic:
        If a WAN segment has > 40 words (~15s), it MUST be split into multiple beats
        to prevent the video from ending while narration is still playing.
        """
        segments = section.get("narration", {}).get("segments", [])
        final_video_prompts = []
        for idx, seg in enumerate(segments):
            # GAP FIX: Verify if visuals are actually required
            directives = seg.get("display_directives", {})
            if directives.get("visual_layer") == "hide":
                continue

            text = seg.get("text", "")
            words = text.split()

            # Fallback for missing segment_id to prevent "None_beat" issue
            seg_id = seg.get("segment_id") or f"seg_{idx + 1}"

            # Fix: Look in root AND render_spec, handle strings vs dicts
            prompts_list = section.get("video_prompts", []) or section.get(
                "render_spec", {}
            ).get("video_prompts", [])
            base_prompt = "Cinematic educational visualization, high quality, professional lighting."
            if (
                prompts_list
                and isinstance(prompts_list, list)
                and len(prompts_list) > 0
            ):
                obj = prompts_list[idx % len(prompts_list)]
                if isinstance(obj, dict):
                    base_prompt = (
                        obj.get("prompt")
                        or obj.get("video_prompt")
                        or obj.get("text")
                        or obj.get("wan_prompt")
                        or base_prompt
                    )
                else:
                    base_prompt = str(obj)

            if len(words) > 40:
                logger.info(
                    f"[Sync Splitter] Segment {seg_id} is too long ({len(words)} words). Splitting into beats."
                )

                # Calculate how many 15s beats we need
                num_beats = (len(words) // 40) + 1

                seg_beats = []
                for i in range(num_beats):
                    # Ensure character consistency by mentioning "Same character as before" in subsequent prompts
                    consistency_prefix = (
                        "Keeping the previous character and setting exactly the same, "
                        if i > 0
                        else ""
                    )

                    beat_id = f"{seg_id}_beat_{i + 1}"
                    final_video_prompts.append(
                        {
                            "beat_id": beat_id,
                            "prompt": f"{consistency_prefix}{base_prompt} (Step {i + 1} of {num_beats})",
                            "duration_hint": 15,
                        }
                    )
                    seg_beats.append(beat_id)

                # Add beat mapping to segment so player knows to switch
                seg["beat_videos"] = seg_beats
            else:
                # Standard segment: still needs a video beat mapping
                beat_id = f"{seg_id}_beat_1"
                final_video_prompts.append(
                    {"beat_id": beat_id, "prompt": base_prompt, "duration_hint": 15}
                )
                seg["beat_videos"] = [beat_id]

        # Replace section top-level video_prompts with the complete mapping
        section["video_prompts"] = final_video_prompts

    def _basic_global_footer_fallback(self, presentation, globals):
        """Minimal fallback if LLM global director fails."""
        summary_bullets = globals.get("summary", {}).get("bullets", [])
        if summary_bullets:
            presentation["sections"].append(
                {
                    "section_id": "summary_fallback",
                    "section_type": "summary",
                    "title": "Lesson Summary",
                    "renderer": "none",
                    "visual_beats": [
                        {
                            "visual_type": "bullet_list",
                            "display_text": "\n".join(
                                f"• {b}" for b in summary_bullets
                            ),
                        }
                    ],
                    "narration": {
                        "segments": [
                            {
                                "segment_id": "summ_1",
                                "text": "To summarize, we've learned: "
                                + ", ".join(summary_bullets),
                            }
                        ]
                    },
                }
            )

    def _add_global_footer_LEGACY(self, presentation, globals):
        # We'll keep the old name but it won't be used by the main flow
        pass

    def _legacy_blind_loop(
        self, markdown_content, subject, grade, images_list, update_status_callback
    ):
        """Character-based chunking fallback if planner fails."""
        chunks = smart_split(markdown_content, target_chars=8000)
        # ... (reuse existing loop logic if needed) ...
        return self.generate_presentation(markdown_content, subject, grade, images_list)

    def validate_director_schema(
        self, data: dict, source_markdown: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate JSON structure AND pointer integrity.
        """
        errors = []

        if "sections" not in data:
            return False, ["Missing 'sections'"]

        for idx, section in enumerate(data.get("sections", [])):
            sec_id = section.get("section_id", f"s{idx}")

            # Check narration segments
            segments = section.get("narration", {}).get("segments", [])
            for s_idx, seg in enumerate(segments):
                # Validating Pointers
                vis = seg.get("visual_content", {})
                pointer = vis.get("markdown_pointer")

                if pointer:
                    start = pointer.get("start_phrase", "")
                    end = pointer.get("end_phrase", "")

                    if not start or not end:
                        errors.append(
                            f"[{sec_id}] Segment {s_idx}: Empty pointer phrases"
                        )
                        continue

                    # SMART VALIDATION: Normalize both phrases and source before comparing
                    # This handles whitespace, punctuation differences while ensuring real matches
                    def normalize_phrase(text):
                        """Normalize text for comparison - collapse spaces, remove formatting artifacts"""
                        import re

                        # Remove extra whitespace
                        text = re.sub(r"\s+", " ", text)
                        # Normalize quotes
                        text = (
                            text.replace('"', '"')
                            .replace('"', '"')
                            .replace("'", "'")
                            .replace("'", "'")
                        )
                        # Remove markdown artifacts that might differ
                        text = text.replace("$$", "$").replace("**", "")
                        return text.strip().lower()

                    start_norm = normalize_phrase(start)
                    end_norm = normalize_phrase(end)
                    source_norm = normalize_phrase(source_markdown)

                    # Check if normalized phrase exists in normalized source
                    start_found = start_norm in source_norm
                    end_found = end_norm in source_norm

                    if not start_found:
                        # Try line-by-line match for better precision
                        start_found = any(
                            start_norm in normalize_phrase(line)
                            for line in source_markdown.split("\n")
                        )

                    if not end_found:
                        end_found = any(
                            end_norm in normalize_phrase(line)
                            for line in source_markdown.split("\n")
                        )

                    if not start_found:
                        errors.append(
                            f"[{sec_id}] Pointer START not found in source: '{start[:30]}...'"
                        )

                    if not end_found:
                        errors.append(
                            f"[{sec_id}] Pointer END not found in source: '{end[:30]}...'"
                        )

        return len(errors) == 0, errors

    async def generate_presentation_parallel(
        self,
        markdown_content: str,
        subject: str = "Science",
        grade: str = "Grade 10",
        images_list: str = "None",
        update_status_callback=None,
    ) -> dict:
        """
        V2.5 PARALLEL Execution Pipeline:
        1. PLANNER: Extracts "Bone" structure (Topics + Global Context).
        2. WORKERS: Runs LLM for every topic + Global sections concurrently.
        3. MERGER: Stitches results into final JSON.
        """
        _, _, _, planner_bone_sys = get_prompts()

        # --- PHASE 1: THE BONE (PLANNER) ---
        msg = "Phase 1: Generating Lesson Blueprint (Parallel Mode)..."
        logger.info(f"DirectorGenerator: {msg}")
        if update_status_callback:
            update_status_callback("planner", msg)

        # No limit for Planner - let the LLM see the full document
        planner_user = f"Subject: {subject}\nGrade: {grade}\n\nDOCUMENT CONTENT:\n{markdown_content}"

        try:
            # Run Planner (Synchronous here, block main thread for 30s is fine)
            planner_response, planner_usage = call_openrouter_llm(
                planner_bone_sys, planner_user, self.config
            )
            blueprint = extract_json_from_response(planner_response)
        except Exception as e:
            logger.error(f"Planner failed: {e}. Falling back to sequential.")
            return self.generate_presentation_loop(
                markdown_content, subject, grade, images_list, update_status_callback
            )

        topics = blueprint.get("topics", [])
        global_context = blueprint.get("global_context", {})
        logger.info(f"DirectorGenerator: Planner identified {len(topics)} topics.")

        # --- PHASE 2: PARALLEL EXECUTION ---
        start_time = time.time()
        tasks = []

        # Task A: Global Worker (Intro/Summary/Recap/Memory)
        tasks.append(self._generate_globals_worker(global_context, subject, grade))

        # Task B: Topic Workers
        for i, topic in enumerate(topics):
            # Extract content strictly
            topic_md = self._extract_topic_markdown(
                markdown_content, topic.get("start_phrase"), topic.get("end_phrase")
            )
            tasks.append(
                self._generate_topic_worker(
                    i, topic, topic_md, subject, grade, images_list
                )
            )

        if update_status_callback:
            update_status_callback(
                "director_loop", f"Phase 2: Blasting {len(tasks)} Parallel Workers..."
            )

        # EXECUTE ALL
        results = await asyncio.gather(*tasks)

        logger.info(
            f"DirectorGenerator: Parallel processing finished in {time.time() - start_time:.2f}s"
        )

        # --- PHASE 3: THE MERGER ---
        output_globals = results[0]  # First result is Globals
        topic_sections = results[1:]  # Rest are topics

        final_presentation = {
            "presentation_title": blueprint.get("presentation_title", "Lesson"),
            "sections": [],
            "metadata": {
                "generated_by": "v2.5-parallel-director",
                "doc_length": len(markdown_content),
                "planner_id": "bone-planner",
            },
        }

        # 1. Intro
        if output_globals.get("intro"):
            final_presentation["sections"].append(output_globals["intro"])

        # 2. Topics (Sorted by original index)
        # Verify order (asyncio.gather preserves order of tasks)
        for sec_list in topic_sections:
            if sec_list:
                final_presentation["sections"].extend(sec_list)

        # 3. Summary/Memory/Recap
        if output_globals.get("summary"):
            final_presentation["sections"].append(output_globals["summary"])
        if output_globals.get("memory"):
            final_presentation["sections"].append(output_globals["memory"])
        if output_globals.get("recap"):
            final_presentation["sections"].append(output_globals["recap"])

        return final_presentation

    async def _generate_topic_worker(
        self, index, topic_meta, topic_md, subject, grade, images_list
    ):
        """Async worker for a single topic."""
        title = topic_meta.get("heading", f"Topic {index + 1}")
        logger.info(f"[Worker {index}] Starting: {title}")

        # Wrap sync LLM call in thread
        try:
            # We use the existing generate_presentation method but run it in thread
            # to avoid blocking the event loop
            data = await asyncio.to_thread(
                self.generate_presentation,
                topic_md,
                subject,
                grade,
                images_list,
                title,  # topic_heading
                self.topic_prompt,  # Use specialized topic prompt
            )
            logger.info(f"[Worker {index}] Finished: {title}")
            return data.get("sections", [])
        except Exception as e:
            logger.error(f"[Worker {index}] Failed: {e}")
            return []

    async def _generate_globals_worker(self, context, subject, grade):
        """
        Async worker to generate Intro, Summary, Memory, Recap via Global LLM.
        """
        logger.info("[Global Worker] Directing global sections via LLM...")

        _, _, _, _, global_system = get_prompts()

        user_prompt = f"Subject: {subject}\nGrade: {grade}\n\nDATA:\n{json.dumps(context, indent=2)}"

        try:
            # We use the same config but this is an async worker,
            # so we'll run the synchronous LLM call in a thread to not block.
            loop = asyncio.get_event_loop()
            response, _ = await loop.run_in_executor(
                None,
                lambda: call_openrouter_llm(global_system, user_prompt, self.config),
            )

            data = extract_json_from_response(response)
            data = normalize_output(data)

            # Extract sections
            final_sections = {}
            for key in ["intro", "summary", "memory", "recap", "quiz"]:
                if key in data:
                    sec = data[key]
                    sec["section_id"] = f"{key}_global"

                    # SYNC SPLITTER
                    if sec.get("renderer") == "video":
                        self._apply_sync_splitter(sec)

                    final_sections[key] = sec

            return final_sections

        except Exception as e:
            logger.error(
                f"[Global Worker] LLM failed: {e}. Falling back to basic construction."
            )
            return self._LEGACY_globals_constructor(context)

    def _LEGACY_globals_constructor(self, context):
        """Backwards compatibility constructor if LLM fails."""
        sections = {}

        # Intro
        sections["intro"] = {
            "section_type": "intro",
            "title": "Introduction",
            "renderer": "none",
            "narration": {
                "segments": [
                    {
                        "segment_id": "intro_1",
                        "text": context.get("intro_narration_context", "Welcome."),
                    }
                ]
            },
        }

        # Summary
        summ_points = context.get("summary_points", [])
        if summ_points:
            sections["summary"] = {
                "section_type": "summary",
                "title": "Summary",
                "renderer": "none",
                "narration": {
                    "segments": [
                        {
                            "segment_id": "summ_1",
                            "text": "Summary: " + ", ".join(summ_points),
                        }
                    ]
                },
            }

        return sections


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
    # Switch to Parallel Generator for V2.5
    return asyncio.run(
        generator.generate_presentation_parallel(
            markdown_content, subject, grade, images_list, update_status_callback
        )
    )
