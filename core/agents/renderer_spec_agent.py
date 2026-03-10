"""
V1.5 Renderer Spec Agent (REQ-013)

Takes visual_beats, outputs renderer-specific specs (manim_scene_spec or video_prompts).
Specialized for each renderer type: manim, video (WAN), remotion.
"""
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent, STRONG_MODEL


class RendererSpecAgent(BaseAgent):
    """
    Renderer Spec Agent - Creates renderer-specific specifications.
    
    Input: section_id, renderer, visual_beats, narration_summary
    Output: section_id, renderer, and corresponding spec (manim_scene_spec, video_prompts, or remotion_scene_spec)
    """
    
    name = "RendererSpec"
    output_schema_file = "render_spec.schema.json"
    model = STRONG_MODEL
    temperature = 0.4
    structural_retries = 2
    semantic_retries = 2
    
    def __init__(self, renderer_type: str = "manim", **kwargs):
        super().__init__(**kwargs)
        self.renderer_type = renderer_type
        
        if renderer_type == "manim":
            self.system_prompt_file = "manim_spec_system_v1.5.txt"
            self.user_prompt_file = "manim_spec_user_v1.5.txt"
        elif renderer_type == "video":
            self.system_prompt_file = "video_prompt_system_v1.5.txt"
            self.user_prompt_file = "video_prompt_user_v1.5.txt"
        elif renderer_type == "remotion":
            self.system_prompt_file = "remotion_spec_system_v1.5.txt"
            self.user_prompt_file = "remotion_spec_user_v1.5.txt"
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")
    
    def validate_structural(self, output: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate renderer spec structure."""
        errors = []
        
        if "section_id" not in output:
            errors.append("Missing 'section_id'")
        
        if "renderer" not in output:
            errors.append("Missing 'renderer'")
        elif output.get("renderer") != self.renderer_type:
            errors.append(f"renderer mismatch: expected '{self.renderer_type}', got '{output.get('renderer')}'")
        
        if self.renderer_type == "manim":
            if "manim_scene_spec" not in output:
                errors.append("Missing 'manim_scene_spec'")
            else:
                spec = output.get("manim_scene_spec", {})
                if "objects" not in spec or not isinstance(spec.get("objects"), list):
                    errors.append("manim_scene_spec missing 'objects' array")
                if "animation_sequence" not in spec or not isinstance(spec.get("animation_sequence"), list):
                    errors.append("manim_scene_spec missing 'animation_sequence' array")
        
        elif self.renderer_type == "video":
            if "video_prompts" not in output:
                errors.append("Missing 'video_prompts'")
            else:
                prompts = output.get("video_prompts", [])
                if not isinstance(prompts, list) or len(prompts) == 0:
                    errors.append("'video_prompts' must be a non-empty array")
                
                for i, p in enumerate(prompts):
                    if "beat_id" not in p:
                        errors.append(f"video_prompt {i}: missing 'beat_id'")
                    if "prompt" not in p:
                        errors.append(f"video_prompt {i}: missing 'prompt'")
                    if "duration_seconds" not in p:
                        errors.append(f"video_prompt {i}: missing 'duration_seconds'")
                    if "style" not in p:
                        errors.append(f"video_prompt {i}: missing 'style'")
        
        elif self.renderer_type == "remotion":
            if "remotion_scene_spec" not in output:
                errors.append("Missing 'remotion_scene_spec'")
            else:
                spec = output.get("remotion_scene_spec", {})
                if "template" not in spec:
                    errors.append("remotion_scene_spec missing 'template'")
                if "props" not in spec:
                    errors.append("remotion_scene_spec missing 'props'")
        
        return len(errors) == 0, errors
    
    def validate_semantic(self, output: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate semantic rules for renderer specs."""
        errors = []
        
        if self.renderer_type == "video":
            prompts = output.get("video_prompts", [])
            is_recap = input_data.get("is_recap", False)
            min_words = 300 if is_recap else 100
            
            banned_phrases = ["etc", "and more", "various", "beautiful", "amazing", "stunning"]
            
            for i, p in enumerate(prompts):
                prompt_text = p.get("prompt", "")
                word_count = len(prompt_text.split())
                
                if word_count < min_words:
                    errors.append(f"video_prompt {i}: only {word_count} words (min {min_words})")
                
                for phrase in banned_phrases:
                    if phrase.lower() in prompt_text.lower():
                        errors.append(f"video_prompt {i}: contains banned vague phrase '{phrase}'")
        
        elif self.renderer_type == "manim":
            spec = output.get("manim_scene_spec", {})
            objects = spec.get("objects", [])
            sequence = spec.get("animation_sequence", [])
            
            object_ids = {obj.get("id") for obj in objects}
            
            for anim in sequence:
                obj_id = anim.get("object_id")
                if isinstance(obj_id, list):
                    for oid in obj_id:
                        if oid not in object_ids:
                            errors.append(f"animation references unknown object_id: {oid}")
                elif obj_id not in object_ids:
                    errors.append(f"animation references unknown object_id: {obj_id}")
        
        return len(errors) == 0, errors
