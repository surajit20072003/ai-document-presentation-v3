import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class JobCertifier:
    """
    Automated Certification for Job Fidelity & Quality.
    Verifies: Architecture, Narration Durations, Global Sections, and Teach-and-Show Logic.
    """
    
    @staticmethod
    def certify_job(job_dir: str) -> str:
        """
        Runs full certification suite and saves report to file.
        Returns short summary string.
        """
        job_path = Path(job_dir)
        pres_path = job_path / "presentation.json"
        report_path = job_path / "certification_report.txt"
        
        if not pres_path.exists():
            return "FAIL: presentation.json not found"
            
        try:
            with open(pres_path, "r", encoding="utf-8") as f:
                pres = json.load(f)
        except Exception as e:
            return f"FAIL: Corrupt JSON - {e}"

        sections = pres.get("sections", [])
        meta = pres.get("metadata", {})
        
        report_lines = []
        report_lines.append(f"====== 🎓 JOB CERTIFICATION REPORT ======")
        report_lines.append(f"Job: {job_path.name}")
        report_lines.append(f"Total Sections: {len(sections)}")
        
        # 1. ARCHITECTURE & PARTITIONING
        chunks = meta.get("chunks", 0)
        report_lines.append("\n[1] ARCHITECTURE")
        report_lines.append(f"Chunks Partitioned: {chunks} {'✅' if chunks > 0 else '❌'}")
        
        # 2. GLOBAL LOGIC (Bookends)
        types = [s.get("section_type") for s in sections]
        report_lines.append("\n[2] GLOBAL SECTIONS (The Bridge)")
        report_lines.append(f"Intro:   {'✅' if 'intro' in types else '❌ (Narrator removed?)'}")
        report_lines.append(f"Summary: {'✅' if 'summary' in types else '❌'}")
        report_lines.append(f"Quiz:    {'✅' if 'quiz' in types else '❌'}")
        report_lines.append(f"Memory:  {'✅' if 'memory' in types else '❌'}")
        report_lines.append(f"Recap:   {'✅' if 'recap' in types else '❌'}")

        # 3. QUIZ & RECAP QUALITY
        if 'quiz' in types:
            try:
                quiz = next(s for s in sections if s['section_type'] == 'quiz')
                qs = quiz.get("questions", [])
                valid_exps = sum(1 for q in qs if q.get("explanation") and len(q.get("explanation")) > 10)
                report_lines.append(f"Quiz Questions: {len(qs)}")
                report_lines.append(f"Narration-Ready Explanations: {valid_exps}/{len(qs)} {'✅' if valid_exps == len(qs) else '⚠️'}")
            except:
                report_lines.append("Quiz Error: Malformed structure")

        if 'recap' in types:
            try:
                recap = next(s for s in sections if s['section_type'] == 'recap')
                prompts = recap.get("video_prompts", [])
                long_prompts = sum(1 for p in prompts if len((p.get("prompt", "") if isinstance(p, dict) else str(p)).split()) > 70)
                report_lines.append(f"Recap 5-Scene Story: {len(prompts)}/5 Scenes {'✅' if len(prompts)==5 else '❌'}")
                report_lines.append(f"Cinematic Detail (>70 words): {long_prompts}/{len(prompts)}")
            except:
                 report_lines.append("Recap Error: Malformed structure")

        # 4. CONTENT & INTELLIGENCE
        report_lines.append("\n[3] CONTENT INTELLIGENCE")
        manim_count = sum(1 for s in sections if s.get("derived_renderer") == "manim")
        video_count = sum(1 for s in sections if s.get("derived_renderer") == "video")
        
        report_lines.append(f"Manim Sections (Math/Physics): {manim_count} {'(Found!)' if manim_count > 0 else '(Standard Slides used)'}")
        report_lines.append(f"Video Sections (Bio/Scenes): {video_count}")

        # 5. TEACH & SHOW FIDELITY
        equations = 0
        images = 0
        total_beats = 0
        zero_durations = 0
        
        for s in sections:
            # Stats
            beats = s.get("visual_beats", [])
            total_beats += len(beats)
            for b in beats:
                if b.get("visual_type") == "equation": equations += 1
                if b.get("visual_type") == "image": images += 1
            
            # Duration Check
            narr = s.get("narration", {})
            if isinstance(narr, dict):
                for seg in narr.get("segments", []):
                    if seg.get("duration_seconds", 0) <= 0:
                        zero_durations += 1

        report_lines.append("\n[4] VISUAL FIDELITY")
        report_lines.append(f"Total Visual Beats: {total_beats}")
        report_lines.append(f"LaTeX Equations: {equations}")
        report_lines.append(f"Injected Images: {images}")
        
        if zero_durations == 0:
            report_lines.append("TTS Duration Check: ✅ PASS (All segments > 0s)")
        else:
            report_lines.append(f"TTS Duration Check: ❌ FAIL ({zero_durations} zero-duration segments)")

        # Save Report
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
            
        summary = f"Certified: {len(sections)} sections. Global: {'✅' if 'intro' in types and 'recap' in types else '⚠️'}. TTS: {'✅' if zero_durations==0 else '❌'}."
        logger.info(summary)
        return summary
