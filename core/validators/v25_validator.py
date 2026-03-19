from typing import List, Dict, Any


class V25Validator:
    """
    Strict Validator for V2.5 Director Bible Compliance.
    Used in Retry Loops to reject non-compliant LLM outputs.
    """

    @staticmethod
    def validate_global_response(data: Dict[str, Any]) -> List[str]:
        """
        Validates the Global Worker output (Intro, Summary, Memory, Recap, Quiz).
        """
        errors = []

        # 1. INTRO (Bible: Clean Start, Text/Visual Hide)
        intro = data.get("intro")
        if not intro:
            errors.append("Missing 'intro' section.")
        else:
            if intro.get("renderer", "none") != "none":
                errors.append(
                    f"Intro renderer must be 'none', got '{intro.get('renderer')}'."
                )

            # Layer Check
            vis_layer = intro.get("visual_layer", "hide")
            txt_layer = intro.get("text_layer", "hide")
            if vis_layer != "hide" or txt_layer != "hide":
                errors.append(
                    f"Intro layers must be hidden. Got visual={vis_layer}, text={txt_layer}."
                )

        # 2. SUMMARY (Bible: Bullet List)
        summary = data.get("summary")
        if not summary:
            errors.append("Missing 'summary' section.")
        else:
            if summary.get("visual_type") != "bullet_list":
                errors.append(
                    f"Summary visual_type must be 'bullet_list', got '{summary.get('visual_type')}'."
                )

        # 3. MEMORY (Bible: Exactly 5 Flashcards)
        memory = data.get("memory")
        if not memory:
            errors.append("Missing 'memory' section.")
        else:
            cards = memory.get("flashcards", [])
            narr_segs = memory.get("narration", {}).get("segments", [])

            if len(cards) != 5:
                errors.append(
                    f"Memory must have exactly 5 flashcards, got {len(cards)}."
                )

            # Bible Rule: 1 Intro + 5 Card Segments = 6 Total
            if len(narr_segs) < 6:
                errors.append(
                    f"Memory must have 6 narration segments (1 Intro + 5 Cards), got {len(narr_segs)}."
                )

        # 4. RECAP (Bible: 5 Segments, Video Renderer)
        recap = data.get("recap")
        if not recap:
            errors.append("Missing 'recap' section.")
        else:
            # V3: Accept text_to_video, video, or wan_video for recap renderer
            if recap.get("renderer") not in ["video", "wan_video", "text_to_video"]:
                errors.append(
                    f"Recap renderer must be 'video'/'wan_video'/'text_to_video', got '{recap.get('renderer')}'."
                )

            # V3: Check for render_spec (new format) OR video_prompts (old format)
            render_spec = recap.get("render_spec", {})
            # Check both inside render_spec AND at top level (for old format compatibility)
            video_prompts_in_spec = render_spec.get("video_prompts", [])
            video_prompts_top = recap.get("video_prompts", [])
            narr_segs = recap.get("narration", {}).get("segments", [])

            # V3 format: render_spec.video_prompts[] (one prompt per segment)
            if video_prompts_in_spec and isinstance(video_prompts_in_spec, list):
                if len(video_prompts_in_spec) != 5:
                    errors.append(
                        f"Recap render_spec.video_prompts must have 5 items. Found {len(video_prompts_in_spec)}."
                    )
            # Old format: top-level video_prompts[]
            elif video_prompts_top and isinstance(video_prompts_top, list):
                if len(video_prompts_top) != 5:
                    errors.append(
                        f"Recap must have 5 video_prompts. Found {len(video_prompts_top)}."
                    )
                    # Word Count Check for old format
                    for i, p in enumerate(video_prompts_top):
                        prompt_text = p if isinstance(p, str) else str(p)
                        cnt = len(prompt_text.split())
                        if cnt < 80:
                            errors.append(
                                f"Recap video_prompt {i} is too short ({cnt} words). Must be 80+ words."
                            )
            # Neither format found - might be single video_prompt
            elif not render_spec.get("video_prompt"):
                errors.append(
                    "Recap must have render_spec.video_prompts[] (5 items) or render_spec.video_prompt or video_prompts[]."
                )

            # Narration segments check
            if len(narr_segs) != 5:
                errors.append(
                    f"Recap must have 5 narration segments. Found {len(narr_segs)}."
                )

        # 5. QUIZ (Optional but Strict if Present)
        quiz = data.get("quiz")
        if quiz:
            # If present, check structure
            # Relaxed: Allow other types (single answer, open ended) per user feedback
            # if quiz.get("visual_type") != "multiple_choice":
            #    errors.append(f"Quiz visual_type must be 'multiple_choice', got '{quiz.get('visual_type')}'.")
            pass

        return errors

    @staticmethod
    def validate_content_chunk(
        data: Dict[str, Any], source_text: str = ""
    ) -> List[str]:
        """
        Validates Content Worker chunks (Content, Example).
        Args:
            data: The JSON output from LLM.
            source_text: The original markdown text for this chunk (for pointer verification).
        """
        sections = data.get("sections", [])
        if not sections and not data.get("section_type"):
            return ["No sections returned from Content Worker."]

        # Normalize to list
        if isinstance(data, dict) and "sections" not in data:
            sections = [data]  # Single section return?

        errors = []
        for i, sec in enumerate(sections):
            stype = sec.get("section_type", "unknown")
            title = sec.get("title", f"Section {i + 1}")

            # 1. QUIZ CHOREOGRAPHY (Bible: 3-Step Dance)
            # Support grouped questions (multiples of 3 segments)
            if stype == "quiz":
                narr_segs = sec.get("narration", {}).get("segments", [])

                if len(narr_segs) == 0 or len(narr_segs) % 3 != 0:
                    errors.append(
                        f"Quiz '{title}' segments count ({len(narr_segs)}) must be a multiple of 3 (3 segments per question)."
                    )
                else:
                    # Strict Choreography Check (Loop through groups)
                    steps = ["introduce", "emphasize", "explain"]
                    num_questions = len(narr_segs) // 3

                    for q_idx in range(num_questions):
                        base = q_idx * 3
                        # Check each step in the trio
                        for step_idx, purpose in enumerate(steps):
                            seg = narr_segs[base + step_idx]
                            if seg.get("purpose") != purpose:
                                errors.append(
                                    f"Quiz '{title}' Q{q_idx + 1} segment {step_idx + 1} purpose must be '{purpose}', got '{seg.get('purpose')}'."
                                )

                        # Pivot Check: Pause Duration (Middle segment)
                        pause_seg = narr_segs[base + 1]
                        if "<pause duration=" not in pause_seg.get("text", ""):
                            errors.append(
                                f"Quiz '{title}' Q{q_idx + 1} Pause segment must contain <pause duration='3'/> tag."
                            )

            if stype in ["content", "example"]:
                # 2. RENDERER & SEGMENT SPECS CHECK
                renderer = sec.get("renderer")
                if not renderer:
                    errors.append(
                        f"Section '{title}' ({stype}) is MISSING 'renderer' key."
                    )

                # Check for segment_specs (V2.5 requirement)
                render_spec = sec.get("render_spec", {})
                segment_specs = render_spec.get("segment_specs", [])

                # Identify SHOW segments
                segments = sec.get("narration", {}).get("segments", [])
                show_seg_ids = {
                    seg["segment_id"]
                    for seg in segments
                    if seg.get("display_directives", {}).get("visual_layer") == "show"
                }

                if show_seg_ids and not segment_specs:
                    # Legacy fallback check
                    v_prompts = render_spec.get("video_prompts", [])
                    m_spec = render_spec.get("manim_scene_spec")
                    if not v_prompts and not m_spec:
                        errors.append(
                            f"Section '{title}': Missing 'segment_specs' for SHOW segments {show_seg_ids}."
                        )

                # Verify each SHOW segment has a spec
                spec_ids = {
                    spec.get("segment_id")
                    for spec in segment_specs
                    if spec.get("segment_id")
                }
                missing_specs = show_seg_ids - spec_ids
                if missing_specs:
                    errors.append(
                        f"Section '{title}': Missing segment_specs for {missing_specs}."
                    )

                # DUPLICATE PROMPT DETECTION (THE BUG FIX)
                all_prompts = []
                for spec in segment_specs:
                    p = spec.get("video_prompt") or spec.get("manim_scene_spec")
                    if p:
                        all_prompts.append(
                            str(p).strip()[:100].lower()
                        )  # Check first 100 chars

                if len(all_prompts) > 1 and len(set(all_prompts)) < len(all_prompts):
                    errors.append(
                        f"Section '{title}': DUPLICATE PROMPTS DETECTED! Ensure each segment has a unique visual description."
                    )

                # Manim Spec Check
                if renderer == "manim":
                    # Check individual specs if available, else root spec
                    if segment_specs:
                        for spec in segment_specs:
                            if spec.get("segment_id") in show_seg_ids:
                                p = spec.get("manim_scene_spec", "")
                                if not p or len(str(p).split()) < 40:
                                    errors.append(
                                        f"Section '{title}' Manim spec for {spec.get('segment_id')} is too short or missing (min 40 words)."
                                    )
                    else:
                        spec = render_spec.get("manim_scene_spec")
                        if not spec or len(str(spec).split()) < 40:
                            errors.append(
                                f"Section '{title}' root manim_scene_spec is too short or missing (min 40 words)."
                            )

                # Video Prompt Check
                if renderer == "video":
                    if segment_specs:
                        for spec in segment_specs:
                            if spec.get("segment_id") in show_seg_ids:
                                p = spec.get("video_prompt", "")
                                # If beat-based, check beats
                                beats = spec.get("beats", [])
                                if beats:
                                    for b in beats:
                                        if len(str(b.get("prompt", "")).split()) < 80:
                                            errors.append(
                                                f"Section '{title}' WAN Beat {b.get('beat_id')} prompt too short."
                                            )
                                elif not p or len(str(p).split()) < 80:
                                    errors.append(
                                        f"Section '{title}' WAN prompt for {spec.get('segment_id')} is too short or missing."
                                    )
                    else:
                        v_prompts = render_spec.get("video_prompts", [])
                        if not v_prompts:
                            errors.append(f"Section '{title}' missing video_prompts.")
                        else:
                            for idx, vp in enumerate(v_prompts):
                                if len(str(vp).split()) < 80:
                                    errors.append(
                                        f"Section '{title}' video_prompt {idx} too short."
                                    )

        return errors
