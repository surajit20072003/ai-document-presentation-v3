"""
Analytics module for tracking LLM pipeline cost and time metrics.
Version 1.2 - Supports 3-pass architecture with per-phase tracking.
"""

import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from core.locks import analytics_lock


# Model pricing per 1M tokens (as of Dec 2024)
MODEL_PRICING = {
    "google/gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "google/gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


@dataclass
class PhaseMetrics:
    """Metrics for a single pipeline phase."""
    phase_name: str
    model: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSMetrics:
    """Metrics for TTS generation."""
    provider: str = "unknown"
    voice: str = "unknown"
    total_segments: int = 0
    total_duration_seconds: float = 0.0
    total_characters: int = 0
    estimated_cost_usd: float = 0.0

@dataclass
class RendererMetrics:
    """Metrics for visual rendering."""
    manim_videos: int = 0
    wan_videos: int = 0
    ltx_videos: int = 0  # V2.6: Added LTX tracking
    static_slides: int = 0
    total_render_time_seconds: float = 0.0
    failed_renders: int = 0
    # V2.6: Beat video tracking
    manim_beat_videos: int = 0
    wan_beat_videos: int = 0
    ltx_beat_videos: int = 0
    section_renders: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AvatarMetrics:
    """Metrics for AI Avatar generation."""
    provider: str = "IndianAvatar"
    total_sections: int = 0
    successful_sections: int = 0
    failed_sections: int = 0
    total_duration_seconds: float = 0.0
    section_details: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ProgressMetrics:
    """Live progress tracking for async operations."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    message: Optional[str] = None
    estimated_remaining_seconds: float = 0.0

@dataclass
class ContentMetrics:
    """Metrics about the generated content."""
    total_sections: int = 0
    total_segments: int = 0
    total_slides: int = 0
    section_types: Dict[str, int] = field(default_factory=dict)
    # ISS-207: Page count from Datalab
    page_count: int = 0
    # ISS-208: Q&A pair count from SmartChunker
    qa_pair_count: int = 0
    # ISS-209/210: Block type counts
    table_count: int = 0
    image_count: int = 0


@dataclass
class ContentCompletenessMetrics:
    """Metrics for Content Completeness Validator."""
    validator_executed: bool = False
    validation_status: str = "not_run"  # not_run, passed, failed, skipped
    execution_time_seconds: float = 0.0
    
    # Validation checks
    word_count_ratio: float = 0.0
    topics_covered: int = 0
    topics_total: int = 0
    topics_coverage_ratio: float = 0.0
    images_referenced: int = 0
    images_total: int = 0
    
    # Retry information
    retry_attempted: bool = False
    retry_success: bool = False
    missing_content_summary: str = ""
    
    # Error tracking
    error: Optional[str] = None


@dataclass
class ValidationMetrics:
    """Validation results for the generated presentation."""
    # Mandatory sections (V2.5 Bible)
    has_intro: bool = False
    has_summary: bool = False
    has_quiz: bool = False
    has_memory: bool = False
    has_recap: bool = False
    mandatory_sections_valid: bool = False
    
    # Quiz validation
    quiz_question_count: int = 0
    flashcard_count: int = 0
    
    # Audio validation
    audio_files_generated: int = 0
    audio_files_expected: int = 0
    audio_success_rate: float = 0.0
    
    # Video validation
    video_files_generated: int = 0
    video_files_expected: int = 0
    video_success_rate: float = 0.0
    manim_success_count: int = 0
    manim_failed_count: int = 0
    wan_success_count: int = 0
    wan_failed_count: int = 0
    ltx_success_count: int = 0  # V2.6: Added LTX tracking
    ltx_failed_count: int = 0
    
    # Beat video sync validation (V2.6)
    beat_videos_expected: int = 0
    beat_videos_linked: int = 0
    beat_videos_on_disk: int = 0
    beat_sync_valid: bool = False
    
    # Avatar validation
    avatar_success_count: int = 0
    avatar_failed_count: int = 0
    avatar_success_rate: float = 0.0
    
    # Overall quality score (0-100)
    quality_score: int = 0
    issues: List[str] = field(default_factory=list)


@dataclass
class PipelineAnalytics:
    """Complete analytics for a pipeline run."""
    job_id: str
    pipeline_version: str = "1.5"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    phases: List[PhaseMetrics] = field(default_factory=list)
    tts: TTSMetrics = field(default_factory=TTSMetrics)
    renderer: RendererMetrics = field(default_factory=RendererMetrics)
    avatar: AvatarMetrics = field(default_factory=AvatarMetrics)
    content: ContentMetrics = field(default_factory=ContentMetrics)
    content_completeness: ContentCompletenessMetrics = field(default_factory=ContentCompletenessMetrics)
    validation: ValidationMetrics = field(default_factory=ValidationMetrics)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    # New Fields for Enhanced Reporting
    progress_details: Dict[str, ProgressMetrics] = field(default_factory=dict)
    timings: Dict[str, float] = field(default_factory=dict)
    
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None


    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["phases"] = [asdict(p) for p in self.phases]
        result["progress_details"] = {k: asdict(v) for k, v in self.progress_details.items()}
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class AnalyticsTracker:
    """Tracks analytics for a pipeline run."""

    def __init__(self, job_id: str):
        self.analytics = PipelineAnalytics(job_id=job_id)
        self._phase_start_times: Dict[str, float] = {}

    def load_from_file(self, filepath: str) -> bool:
        """Load analytics from a JSON file if it exists."""
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            # Reconstruct the objects manually to ensure types are correct
            self.analytics.pipeline_version = data.get("pipeline_version", "1.5")
            self.analytics.started_at = data.get("started_at")
            self.analytics.completed_at = data.get("completed_at")
            self.analytics.total_duration_seconds = data.get("total_duration_seconds", 0.0)
            self.analytics.total_cost_usd = data.get("total_cost_usd", 0.0)
            self.analytics.total_input_tokens = data.get("total_input_tokens", 0)
            self.analytics.total_output_tokens = data.get("total_output_tokens", 0)
            self.analytics.status = data.get("status", "pending")
            self.analytics.error = data.get("error")
            
            # Content
            c = data.get("content", {})
            self.analytics.content = ContentMetrics(**{k: v for k, v in c.items() if k in ContentMetrics.__annotations__})
            
            # TTS
            t = data.get("tts", {})
            self.analytics.tts = TTSMetrics(**{k: v for k, v in t.items() if k in TTSMetrics.__annotations__})
            
            # Renderer
            r = data.get("renderer", {})
            self.analytics.renderer = RendererMetrics(**{k: v for k, v in r.items() if k in RendererMetrics.__annotations__})
            
            # Avatar
            a = data.get("avatar", {})
            self.analytics.avatar = AvatarMetrics(**{k: v for k, v in a.items() if k in AvatarMetrics.__annotations__})
            
            # Phases
            self.analytics.phases = []
            for p in data.get("phases", []):
                self.analytics.phases.append(PhaseMetrics(**{k: v for k, v in p.items() if k in PhaseMetrics.__annotations__}))

            # Progress Details (Enhanced)
            pd = data.get("progress_details", {})
            self.analytics.progress_details = {}
            for k, v in pd.items():
                self.analytics.progress_details[k] = ProgressMetrics(**{pk: pv for pk, pv in v.items() if pk in ProgressMetrics.__annotations__})

            # Timings
            self.analytics.timings = data.get("timings", {})

            return True
        except Exception as e:
            print(f"[Analytics] Failed to load {filepath}: {e}")
            return False

    def start_pipeline(self) -> None:
        """Mark pipeline start."""
        self.analytics.started_at = datetime.utcnow().isoformat()
        self.analytics.status = "running"

    def end_pipeline(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark pipeline end and calculate totals."""
        self.analytics.completed_at = datetime.utcnow().isoformat()
        self.analytics.status = status
        self.analytics.error = error

        # Calculate totals
        if self.analytics.started_at:
            start = datetime.fromisoformat(self.analytics.started_at)
            end = datetime.fromisoformat(self.analytics.completed_at)
            self.analytics.total_duration_seconds = (end - start).total_seconds()

        self.analytics.total_cost_usd = sum(p.cost_usd for p in self.analytics.phases)
        self.analytics.total_input_tokens = sum(p.input_tokens for p in self.analytics.phases)
        self.analytics.total_output_tokens = sum(p.output_tokens for p in self.analytics.phases)

    def start_phase(self, phase_name: str, model: str, metadata: Optional[Dict] = None) -> PhaseMetrics:
        """Start tracking a new phase."""
        phase = PhaseMetrics(
            phase_name=phase_name,
            model=model,
            started_at=datetime.utcnow().isoformat(),
            status="running",
            metadata=metadata or {}
        )
        self._phase_start_times[phase_name] = time.time()
        self.analytics.phases.append(phase)
        return phase

    def end_phase(
        self,
        phase_name: str,
        input_tokens: int,
        output_tokens: int,
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[PhaseMetrics]:
        """End tracking for a phase and calculate metrics."""
        phase = self._find_phase(phase_name)
        if not phase:
            return None

        phase.completed_at = datetime.utcnow().isoformat()
        phase.status = status
        phase.error = error
        phase.input_tokens = input_tokens
        phase.output_tokens = output_tokens
        phase.total_tokens = input_tokens + output_tokens

        # Calculate duration
        if phase_name in self._phase_start_times:
            phase.duration_seconds = time.time() - self._phase_start_times[phase_name]

        # Calculate cost
        phase.cost_usd = self._calculate_cost(phase.model, input_tokens, output_tokens)

        # Update timings map
        self.analytics.timings[phase_name] = phase.duration_seconds

        return phase

    def add_llm_call(
        self,
        phase: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> PhaseMetrics:
        """Add a completed LLM call as a phase (convenience method for V1.5 agents)."""
        phase_obj = PhaseMetrics(
            phase_name=phase,
            model=model,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            status="completed",
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            duration_seconds=0.0,
            cost_usd=self._calculate_cost(model, prompt_tokens, completion_tokens)
        )
        self.analytics.phases.append(phase_obj)
        return phase_obj

    def set_tts_metrics(
        self,
        provider: str,
        voice: str,
        total_segments: int,
        total_duration: float,
        total_characters: int,
        estimated_cost: float = 0.0
    ) -> None:
        """Set TTS generation metrics."""
        self.analytics.tts = TTSMetrics(
            provider=provider,
            voice=voice,
            total_segments=total_segments,
            total_duration_seconds=total_duration,
            total_characters=total_characters,
            estimated_cost_usd=estimated_cost
        )

    def set_renderer_metrics(
        self,
        manim_videos: int = 0,
        wan_videos: int = 0,
        ltx_videos: int = 0,
        static_slides: int = 0,
        render_time: float = 0.0,
        failed_renders: int = 0,
        manim_beat_videos: int = 0,
        wan_beat_videos: int = 0,
        ltx_beat_videos: int = 0
    ) -> None:
        """Set visual rendering metrics."""
        self.analytics.renderer.manim_videos = manim_videos
        self.analytics.renderer.wan_videos = wan_videos
        self.analytics.renderer.ltx_videos = ltx_videos
        self.analytics.renderer.static_slides = static_slides
        self.analytics.renderer.total_render_time_seconds = render_time
        self.analytics.renderer.failed_renders = failed_renders
        self.analytics.renderer.manim_beat_videos = manim_beat_videos
        self.analytics.renderer.wan_beat_videos = wan_beat_videos
        self.analytics.renderer.ltx_beat_videos = ltx_beat_videos

    def add_render_detail(self, section_id: str, section_type: str, renderer: str, duration: float, status: str, metadata: Optional[Dict] = None, retry_action: Optional[str] = None) -> None:
        """Add detail for a single section render."""
        render_data = {
            "section_id": section_id,
            "section_type": section_type,
            "renderer": renderer,
            "duration_seconds": round(duration, 2),
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        if retry_action:
            render_data["retry_action"] = retry_action
            
        self.analytics.renderer.section_renders.append(render_data)

    def update_progress(self, category: str, completed: int, total: int, failed: int = 0, message: Optional[str] = None) -> None:
        """Update live progress for a category (e.g., 'avatar_generation')."""
        remaining = total - (completed + failed)
        
        # Simple estimation logic: (avg time per item) * remaining
        # Ideally this should be based on actual measured rate
        est_seconds = 0.0 
        
        self.analytics.progress_details[category] = ProgressMetrics(
            total=total,
            completed=completed,
            failed=failed,
            pending=remaining,
            message=message,
            estimated_remaining_seconds=est_seconds
        )

    def set_avatar_metrics(
        self,
        total_sections: int,
        successful: int,
        failed: int,
        duration: float
    ) -> None:
        """Set AI Avatar metrics summary."""
        self.analytics.avatar.total_sections = total_sections
        self.analytics.avatar.successful_sections = successful
        self.analytics.avatar.failed_sections = failed
        self.analytics.avatar.total_duration_seconds = duration

    def add_avatar_detail(self, section_id: str, duration: float, status: str, error: Optional[str] = None) -> None:
        """Add detail for a single section avatar generation."""
        self.analytics.avatar.section_details.append({
            "section_id": section_id,
            "duration_seconds": round(duration, 2),
            "status": status,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })

    def set_content_metrics(
        self,
        total_sections: int,
        total_segments: int,
        total_slides: int,
        section_types: Optional[Dict[str, int]] = None,
        page_count: int = 0,
        qa_pair_count: int = 0,
        table_count: int = 0,
        image_count: int = 0
    ) -> None:
        """Set content generation metrics.
        
        ISS-207: Added page_count from Datalab
        ISS-208: Added qa_pair_count from SmartChunker
        ISS-209/210: Added table_count and image_count
        """
        self.analytics.content = ContentMetrics(
            total_sections=total_sections,
            total_segments=total_segments,
            total_slides=total_slides,
            section_types=section_types if section_types else {},
            page_count=page_count,
            qa_pair_count=qa_pair_count,
            table_count=table_count,
            image_count=image_count
        )

    def set_content_completeness_metrics(
        self,
        executed: bool,
        validation_status: str,
        execution_time: float,
        word_count_ratio: float = 0.0,
        topics_covered: int = 0,
        topics_total: int = 0,
        images_referenced: int = 0,
        images_total: int = 0,
        retry_attempted: bool = False,
        retry_success: bool = False,
        missing_content: str = "",
        error: Optional[str] = None
    ) -> None:
        """Set Content Completeness Validator metrics."""
        topics_ratio = (topics_covered / topics_total) if topics_total > 0 else 1.0
        
        self.analytics.content_completeness = ContentCompletenessMetrics(
            validator_executed=executed,
            validation_status=validation_status,
            execution_time_seconds=execution_time,
            word_count_ratio=word_count_ratio,
            topics_covered=topics_covered,
            topics_total=topics_total,
            topics_coverage_ratio=topics_ratio,
            images_referenced=images_referenced,
            images_total=images_total,
            retry_attempted=retry_attempted,
            retry_success=retry_success,
            missing_content_summary=missing_content,
            error=error
        )

    def set_validation_metrics(
        self,
        section_types: Dict[str, int],
        quiz_question_count: int = 0,
        flashcard_count: int = 0,
        audio_generated: int = 0,
        audio_expected: int = 0,
        video_generated: int = 0,
        video_expected: int = 0,
        manim_success: int = 0,
        manim_failed: int = 0,
        wan_success: int = 0,
        wan_failed: int = 0,
        ltx_success: int = 0,
        ltx_failed: int = 0,
        avatar_success: int = 0,
        avatar_failed: int = 0,
        beat_videos_expected: int = 0,
        beat_videos_linked: int = 0,
        beat_videos_on_disk: int = 0
    ) -> None:
        """Set comprehensive validation metrics for the job.
        
        Validates against V2.5 Director Bible requirements:
        - Mandatory sections: intro, summary, memory, recap
        - Optional: quiz (depends on content)
        - Audio, video, avatar generation success rates
        """
        # Check mandatory sections
        has_intro = section_types.get("intro", 0) >= 1
        has_summary = section_types.get("summary", 0) >= 1
        has_memory = section_types.get("memory", 0) >= 1
        has_recap = section_types.get("recap", 0) >= 1
        has_quiz = section_types.get("quiz", 0) >= 1
        
        mandatory_valid = has_intro and has_summary and has_memory and has_recap
        
        # Calculate success rates
        audio_rate = (audio_generated / audio_expected * 100) if audio_expected > 0 else 0.0
        video_rate = (video_generated / video_expected * 100) if video_expected > 0 else 0.0
        avatar_total = avatar_success + avatar_failed
        avatar_rate = (avatar_success / avatar_total * 100) if avatar_total > 0 else 0.0
        
        # Calculate quality score (0-100)
        issues = []
        score = 100
        
        # Mandatory sections (30 points)
        if not has_intro:
            score -= 8
            issues.append("Missing intro section")
        if not has_summary:
            score -= 8
            issues.append("Missing summary section")
        if not has_memory:
            score -= 7
            issues.append("Missing memory section")
        if not has_recap:
            score -= 7
            issues.append("Missing recap section")
        
        # Audio generation (25 points)
        if audio_expected > 0:
            if audio_rate < 100:
                audio_penalty = int((100 - audio_rate) * 0.25)
                score -= audio_penalty
                if audio_rate == 0:
                    issues.append("No audio files generated")
                else:
                    issues.append(f"Audio generation incomplete: {audio_generated}/{audio_expected}")
        
        # Video generation (25 points)
        if video_expected > 0 and video_rate < 100:
            video_penalty = int((100 - video_rate) * 0.25)
            score -= video_penalty
            if video_rate == 0:
                issues.append("No video files generated")
            else:
                issues.append(f"Video generation incomplete: {video_generated}/{video_expected}")
        
        # Avatar generation (20 points)
        if avatar_total > 0 and avatar_rate < 100:
            avatar_penalty = int((100 - avatar_rate) * 0.20)
            score -= avatar_penalty
            if avatar_rate == 0:
                issues.append("No avatar files generated")
            else:
                issues.append(f"Avatar generation incomplete: {avatar_success}/{avatar_total}")
        
        score = max(0, score)
        
        # Beat sync validation
        beat_sync_valid = (beat_videos_expected == beat_videos_linked == beat_videos_on_disk) if beat_videos_expected > 0 else True
        if not beat_sync_valid:
            issues.append(f"Beat video sync mismatch: expected={beat_videos_expected}, linked={beat_videos_linked}, on_disk={beat_videos_on_disk}")
        
        self.analytics.validation = ValidationMetrics(
            has_intro=has_intro,
            has_summary=has_summary,
            has_quiz=has_quiz,
            has_memory=has_memory,
            has_recap=has_recap,
            mandatory_sections_valid=mandatory_valid,
            quiz_question_count=quiz_question_count,
            flashcard_count=flashcard_count,
            audio_files_generated=audio_generated,
            audio_files_expected=audio_expected,
            audio_success_rate=round(audio_rate, 1),
            video_files_generated=video_generated,
            video_files_expected=video_expected,
            video_success_rate=round(video_rate, 1),
            manim_success_count=manim_success,
            manim_failed_count=manim_failed,
            wan_success_count=wan_success,
            wan_failed_count=wan_failed,
            ltx_success_count=ltx_success,
            ltx_failed_count=ltx_failed,
            beat_videos_expected=beat_videos_expected,
            beat_videos_linked=beat_videos_linked,
            beat_videos_on_disk=beat_videos_on_disk,
            beat_sync_valid=beat_sync_valid,
            avatar_success_count=avatar_success,
            avatar_failed_count=avatar_failed,
            avatar_success_rate=round(avatar_rate, 1),
            quality_score=score,
            issues=issues
        )

    def track_decision(
        self,
        agent_name: str,
        decision_type: str,
        options: List[str],
        selected: str,
        reason: str
    ) -> None:
        """Track an AI decision."""
        self.analytics.decisions.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "decision_type": decision_type,
            "options": options,
            "selected": selected,
            "reason": reason
        })

    def _find_phase(self, phase_name: str) -> Optional[PhaseMetrics]:
        """Find a phase by name."""
        for phase in self.analytics.phases:
            if phase.phase_name == phase_name:
                return phase
        return None

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            # Try partial match
            for model_key, prices in MODEL_PRICING.items():
                if model_key in model or model in model_key:
                    pricing = prices
                    break

        if not pricing:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the pipeline analytics."""
        # Calculate total estimated cost including TTS
        tts_cost = self.analytics.tts.estimated_cost_usd if self.analytics.tts else 0.0
        total_cost = self.analytics.total_cost_usd + tts_cost
        
        return {
            "job_id": self.analytics.job_id,
            "pipeline_version": self.analytics.pipeline_version,
            "status": self.analytics.status,
            "error": self.analytics.error,
            "started_at": self.analytics.started_at,
            "completed_at": self.analytics.completed_at,
            "total_duration_seconds": round(self.analytics.total_duration_seconds, 2),
            "total_cost_usd": round(total_cost, 4),
            "llm_cost_usd": round(self.analytics.total_cost_usd, 4),
            "total_tokens": self.analytics.total_input_tokens + self.analytics.total_output_tokens,
            "input_tokens": self.analytics.total_input_tokens,
            "output_tokens": self.analytics.total_output_tokens,
            "phases_completed": len([p for p in self.analytics.phases if p.status == "completed"]),
            "phases_failed": len([p for p in self.analytics.phases if p.status == "failed"]),
            "tts": {
                "provider": self.analytics.tts.provider,
                "voice": self.analytics.tts.voice,
                "segments": self.analytics.tts.total_segments,
                "duration_seconds": round(self.analytics.tts.total_duration_seconds, 2),
                "characters": self.analytics.tts.total_characters,
                "cost_usd": round(self.analytics.tts.estimated_cost_usd, 4)
            } if self.analytics.tts else {},
            "renderer": {
                "manim_videos": self.analytics.renderer.manim_videos,
                "wan_videos": self.analytics.renderer.wan_videos,
                "static_slides": self.analytics.renderer.static_slides,
                "render_time_seconds": round(self.analytics.renderer.total_render_time_seconds, 2),
                "failed_renders": self.analytics.renderer.failed_renders,
                "details": self.analytics.renderer.section_renders
            } if self.analytics.renderer else {},
            "avatar": {
                "provider": self.analytics.avatar.provider,
                "total_sections": self.analytics.avatar.total_sections,
                "successful_sections": self.analytics.avatar.successful_sections,
                "failed_sections": self.analytics.avatar.failed_sections,
                "total_duration_seconds": round(self.analytics.avatar.total_duration_seconds, 2),
                "details": self.analytics.avatar.section_details
            } if self.analytics.avatar else {},
            "progress": {k: asdict(v) for k, v in self.analytics.progress_details.items()},
            "timings": self.analytics.timings,
            "content": {
                "sections": self.analytics.content.total_sections,
                "segments": self.analytics.content.total_segments,
                "slides": self.analytics.content.total_slides,
                "section_types": self.analytics.content.section_types,
                "page_count": self.analytics.content.page_count,
                "qa_pair_count": self.analytics.content.qa_pair_count,
                "table_count": self.analytics.content.table_count,
                "image_count": self.analytics.content.image_count
            } if self.analytics.content else {},
            "content_completeness": {
                "executed": self.analytics.content_completeness.validator_executed,
                "status": self.analytics.content_completeness.validation_status,
                "execution_time_seconds": round(self.analytics.content_completeness.execution_time_seconds, 2),
                "word_count_ratio": round(self.analytics.content_completeness.word_count_ratio, 2),
                "topics_coverage": {
                    "covered": self.analytics.content_completeness.topics_covered,
                    "total": self.analytics.content_completeness.topics_total,
                    "ratio": round(self.analytics.content_completeness.topics_coverage_ratio, 2)
                },
                "images": {
                    "referenced": self.analytics.content_completeness.images_referenced,
                    "total": self.analytics.content_completeness.images_total
                },
                "retry_attempted": self.analytics.content_completeness.retry_attempted,
                "retry_success": self.analytics.content_completeness.retry_success,
                "error": self.analytics.content_completeness.error
            } if self.analytics.content_completeness.validator_executed else {"executed": False},
            "validation": {
                "mandatory_sections_valid": self.analytics.validation.mandatory_sections_valid,
                "has_intro": self.analytics.validation.has_intro,
                "has_summary": self.analytics.validation.has_summary,
                "has_quiz": self.analytics.validation.has_quiz,
                "has_memory": self.analytics.validation.has_memory,
                "has_recap": self.analytics.validation.has_recap,
                "quiz_question_count": self.analytics.validation.quiz_question_count,
                "flashcard_count": self.analytics.validation.flashcard_count,
                "audio": {
                    "generated": self.analytics.validation.audio_files_generated,
                    "expected": self.analytics.validation.audio_files_expected,
                    "success_rate": self.analytics.validation.audio_success_rate
                },
                "video": {
                    "generated": self.analytics.validation.video_files_generated,
                    "expected": self.analytics.validation.video_files_expected,
                    "success_rate": self.analytics.validation.video_success_rate,
                    "manim_success": self.analytics.validation.manim_success_count,
                    "manim_failed": self.analytics.validation.manim_failed_count,
                    "wan_success": self.analytics.validation.wan_success_count,
                    "wan_failed": self.analytics.validation.wan_failed_count,
                    "ltx_success": self.analytics.validation.ltx_success_count,
                    "ltx_failed": self.analytics.validation.ltx_failed_count
                },
                "beat_sync": {
                    "expected": self.analytics.validation.beat_videos_expected,
                    "linked": self.analytics.validation.beat_videos_linked,
                    "on_disk": self.analytics.validation.beat_videos_on_disk,
                    "valid": self.analytics.validation.beat_sync_valid
                },
                "avatar": {
                    "success": self.analytics.validation.avatar_success_count,
                    "failed": self.analytics.validation.avatar_failed_count,
                    "success_rate": self.analytics.validation.avatar_success_rate
                },
                "quality_score": self.analytics.validation.quality_score,
                "issues": self.analytics.validation.issues
            } if self.analytics.validation else {},
            "phase_breakdown": {
                p.phase_name: {
                    "cost_usd": round(p.cost_usd, 4),
                    "duration_seconds": round(p.duration_seconds, 2),
                    "tokens": p.total_tokens,
                    "model": p.model,
                    "status": p.status
                }
                for p in self.analytics.phases
            }
        }

    def save_to_file(self, filepath: str) -> None:
        """Save analytics to a JSON file."""
        with analytics_lock:
            with open(filepath, "w") as f:
                f.write(self.analytics.to_json())

    def print_summary(self) -> None:
        """Print a formatted summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print(f"PIPELINE ANALYTICS - Job {summary['job_id']}")
        print("=" * 60)
        print(f"Status: {summary['status']}")
        print(f"Total Duration: {summary['total_duration_seconds']:.2f}s")
        print(f"Total Cost: ${summary['total_cost_usd']:.4f}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Phases: {summary['phases_completed']} completed, {summary['phases_failed']} failed")
        print("-" * 60)
        print("PHASE BREAKDOWN:")
        for phase_name, data in summary["phase_breakdown"].items():
            print(f"  {phase_name}:")
            print(f"    Duration: {data['duration_seconds']:.2f}s")
            print(f"    Cost: ${data['cost_usd']:.4f}")
            print(f"    Tokens: {data['tokens']:,}")
        print("-" * 60)
        print("VALIDATION:")
        val = summary.get("validation", {})
        print(f"  Quality Score: {val.get('quality_score', 'N/A')}/100")
        print(f"  Mandatory Sections: {'✅' if val.get('mandatory_sections_valid') else '❌'}")
        if val.get("issues"):
            print(f"  Issues: {', '.join(val['issues'])}")
        print("=" * 60 + "\n")


# Convenience functions for integration
def create_tracker(job_id: str) -> AnalyticsTracker:
    """Create a new analytics tracker for a job."""
    return AnalyticsTracker(job_id)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a single LLM call."""
    tracker = AnalyticsTracker("estimate")
    return tracker._calculate_cost(model, input_tokens, output_tokens)
