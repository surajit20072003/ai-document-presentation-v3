"""
V1.5 Section Planner Agent (REQ-010)

Takes topics from Chunker, outputs section blueprints with metadata.
Each blueprint defines: section type, title, renderer choice, avatar settings.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent


class SectionPlannerAgent(BaseAgent):
    """
    Section Planner Agent - Plans the presentation structure.
    
    Input: topics (from Chunker), subject, grade
    Output: Array of SectionBlueprint objects
    """
    
    name = "SectionPlanner"
    system_prompt_file = "section_planner_system_v1.5.txt"
    user_prompt_file = "section_planner_user_v1.5.txt"
    output_schema_file = "section_blueprint.schema.json"
    model = "google/gemini-2.5-flash"
    temperature = 0.3
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate the sections array structure."""
        errors = []
        
        if "sections" not in output:
            errors.append("Missing 'sections' array")
            return False, errors
        
        sections = output.get("sections", [])
        if not isinstance(sections, list) or len(sections) == 0:
            errors.append("'sections' must be a non-empty array")
            return False, errors
        
        required_fields = [
            "section_id", "section_type", "title", "source_topics",
            "learning_goals", "suggested_renderer", "renderer_reasoning",
            "avatar_visibility", "avatar_position", "estimated_duration_seconds",
            "budgets"  # V1.5.1: Dynamic budgets are now required
        ]
        
        valid_section_types = ["intro", "summary", "content", "example", "quiz", "memory", "recap"]
        valid_renderers = ["manim", "video", "none"]  # remotion removed per user request
        valid_visibility = ["required", "optional", "hidden"]
        valid_positions = ["left", "right", "center", "hidden"]
        
        for i, section in enumerate(sections):
            for field in required_fields:
                if field not in section:
                    errors.append(f"Section {i}: missing required field '{field}'")
            
            if "section_type" in section and section["section_type"] not in valid_section_types:
                errors.append(f"Section {i}: invalid section_type '{section.get('section_type')}'")
            
            if "suggested_renderer" in section and section["suggested_renderer"] not in valid_renderers:
                errors.append(f"Section {i}: invalid suggested_renderer '{section.get('suggested_renderer')}'")
            
            if "avatar_visibility" in section and section["avatar_visibility"] not in valid_visibility:
                errors.append(f"Section {i}: invalid avatar_visibility '{section.get('avatar_visibility')}'")
            
            if "avatar_position" in section and section["avatar_position"] not in valid_positions:
                errors.append(f"Section {i}: invalid avatar_position '{section.get('avatar_position')}'")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for section planning."""
        errors = []
        sections = output.get("sections", [])
        
        if not sections:
            errors.append("No sections found")
            return False, errors
        
        section_types = [s.get("section_type") for s in sections]
        
        if section_types.count("intro") != 1:
            errors.append(f"Must have exactly 1 intro section, found {section_types.count('intro')}")
        
        if section_types.count("summary") != 1:
            errors.append(f"Must have exactly 1 summary section, found {section_types.count('summary')}")
        
        if section_types.count("memory") != 1:
            errors.append(f"Must have exactly 1 memory section, found {section_types.count('memory')}")
        
        if section_types.count("recap") != 1:
            errors.append(f"Must have exactly 1 recap section, found {section_types.count('recap')}")
        
        if sections[0].get("section_type") != "intro":
            errors.append("First section must be 'intro'")
        
        if len(sections) > 1 and sections[1].get("section_type") != "summary":
            errors.append("Second section must be 'summary'")
        
        if sections[-1].get("section_type") != "recap":
            errors.append("Last section must be 'recap'")
        
        if len(sections) >= 2 and sections[-2].get("section_type") != "memory":
            errors.append("Second-to-last section must be 'memory'")
        
        content_count = section_types.count("content") + section_types.count("example")
        if content_count < 1:
            errors.append("Must have at least 1 content or example section")
        
        for i, section in enumerate(sections):
            st = section.get("section_type")
            renderer = section.get("suggested_renderer")
            
            if st in ["intro", "summary", "quiz", "memory"] and renderer != "none":
                errors.append(f"Section {i} ({st}): renderer must be 'none' for {st} sections")
            
            if st == "recap" and renderer != "video":
                errors.append(f"Section {i} (recap): renderer must be 'video' for recap sections")
        
        expected_order = ["intro", "summary"]
        actual_order = section_types[:2]
        if actual_order != expected_order:
            errors.append(f"Section order must start with intro, summary. Got: {actual_order}")
        
        return len(errors) == 0, errors
