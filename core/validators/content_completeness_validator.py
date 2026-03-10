"""
Content Completeness Validator - V2.5 Pipeline Validation Checkpoint

Validates that presentation.json has captured 100% of content from source markdown
before expensive asset generation (Manim/WAN/Avatar) begins.

Validation Checks:
1. Image Coverage - All images from source are referenced
2. Topic Coverage - All Smart Chunker topics are present
3. Key Terms - All important terms are included
4. Content Volume - Word count preserved within tolerance

Author: AI Document Presentation Pipeline
Version: 1.0
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class ContentCompletenessValidator:
    """
    Validates that presentation.json captures all source markdown content.
    
    Usage:
        validator = ContentCompletenessValidator()
        result = validator.validate(
            presentation=presentation_dict,
            chunker_output_path="jobs/abc123/artifacts/01_chunker.json",
            images_dir="jobs/abc123/images",
            source_markdown=markdown_content
        )
    """
    
    def __init__(self, tolerance_percent: float = 20.0):
        """
        Initialize validator.
        
        Args:
            tolerance_percent: Acceptable word count variance (default 20%)
        """
        self.tolerance_percent = tolerance_percent
        
    def validate(
        self,
        presentation: Dict,
        chunker_output_path: str,
        images_dir: str,
        source_markdown: str
    ) -> Dict:
        """
        Run all validation checks.
        
        Args:
            presentation: presentation.json dict
            chunker_output_path: Path to 01_chunker.json (ground truth)
            images_dir: Path to images directory
            source_markdown: Original markdown content
            
        Returns:
            Validation result dict with status and detailed findings
        """
        logger.info("[ContentCompletenessValidator] Starting validation...")
        
        results = {
            "validation_status": "passed",
            "checks": {},
            "retry_prompt_enhancement": ""
        }
        
        # Load chunker output (ground truth)
        chunker_data = self._load_chunker_output(chunker_output_path)
        if not chunker_data:
            logger.warning("Chunker output not found - skipping validation")
            results["validation_status"] = "skipped"
            results["error"] = "Chunker output file not found"
            return results
        
        # Run validation checks
        image_check = self._validate_image_coverage(presentation, images_dir)
        topic_check = self._validate_topic_coverage(presentation, chunker_data)
        terms_check = self._validate_key_terms(presentation, chunker_data)
        volume_check = self._validate_content_volume(presentation, source_markdown)
        
        results["checks"] = {
            "image_coverage": image_check,
            "topic_coverage": topic_check,
            "key_terms": terms_check,
            "content_volume": volume_check
        }
        
        # Determine overall status
        failed_checks = [
            name for name, check in results["checks"].items()
            if check.get("status") == "failed"
        ]
        
        if failed_checks:
            results["validation_status"] = "failed"
            results["retry_prompt_enhancement"] = self._build_retry_prompt(results["checks"])
            logger.warning(f"Validation FAILED. Failed checks: {failed_checks}")
        else:
            logger.info("Validation PASSED ✓")
        
        return results
    
    def _load_chunker_output(self, path: str) -> Optional[Dict]:
        """Load Smart Chunker output JSON."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Chunker output not found: {path}")
            return None
        except Exception as e:
            logger.error(f"Error loading chunker output: {e}")
            return None
    
    def _validate_image_coverage(self, presentation: Dict, images_dir: str) -> Dict:
        """
        Validate that all extracted images are referenced in presentation.json.
        
        Returns:
            {
                "status": "passed" | "failed",
                "total_images": int,
                "referenced_images": int,
                "missing_images": [str],
                "orphaned_references": [str]
            }
        """
        logger.info("[ImageCoverage] Checking image references...")
        
        # Get all image files in images directory
        images_path = Path(images_dir)
        if not images_path.exists():
            return {
                "status": "passed",
                "total_images": 0,
                "referenced_images": 0,
                "missing_images": [],
                "orphaned_references": [],
                "note": "No images directory found"
            }
        
        image_files = set()
        for ext in [".png", ".jpg", ".jpeg"]:
            image_files.update([f.name for f in images_path.glob(f"*{ext}")])
        
        # Normalize to .png (our standard format)
        image_files = {img.replace(".jpeg", ".png").replace(".jpg", ".png") for img in image_files}
        
        # Extract all image references from presentation.json
        referenced_images = set()
        for section in presentation.get("sections", []):
            # Check narration segments
            for segment in section.get("narration", {}).get("segments", []):
                visual_content = segment.get("visual_content", {})
                if isinstance(visual_content, dict):
                    image_id = visual_content.get("image_id")
                    image_path = visual_content.get("image_path")
                    
                    if image_id:
                        # Normalize extension
                        image_id = image_id.replace(".jpeg", ".png").replace(".jpg", ".png")
                        referenced_images.add(image_id)
                    if image_path:
                        # Extract filename from path
                        filename = Path(image_path).name
                        filename = filename.replace(".jpeg", ".png").replace(".jpg", ".png")
                        referenced_images.add(filename)
        
        # Find missing images (in directory but not referenced)
        missing_images = sorted(list(image_files - referenced_images))
        
        # Find orphaned references (referenced but not in directory)
        orphaned_references = sorted(list(referenced_images - image_files))
        
        status = "passed" if not missing_images else "failed"
        
        result = {
            "status": status,
            "total_images": len(image_files),
            "referenced_images": len(referenced_images),
            "missing_images": missing_images,
            "orphaned_references": orphaned_references
        }
        
        if missing_images:
            logger.warning(f"Missing image references: {missing_images}")
        
        return result
    
    def _validate_topic_coverage(self, presentation: Dict, chunker_data: Dict) -> Dict:
        """
        Validate that all Smart Chunker topics appear in presentation.json.
        
        Returns:
            {
                "status": "passed" | "failed",
                "total_topics": int,
                "covered_topics": int,
                "missing_topics": [{"topic_id": str, "title": str}]
            }
        """
        logger.info("[TopicCoverage] Checking topic coverage...")
        
        # Get topics from chunker (ground truth)
        chunker_topics = chunker_data.get("topics", [])
        if not chunker_topics:
            return {
                "status": "passed",
                "total_topics": 0,
                "covered_topics": 0,
                "missing_topics": [],
                "note": "No topics in chunker output"
            }
        
        # Build set of topic IDs and titles from chunker
        expected_topic_ids = {t.get("topic_id") for t in chunker_topics if t.get("topic_id")}
        expected_topic_titles = {t.get("title", "").lower() for t in chunker_topics if t.get("title")}
        
        # Extract topics from presentation sections
        found_topic_ids = set()
        found_topic_titles = set()
        
        for section in presentation.get("sections", []):
            # Check topic_id field
            topic_id = section.get("topic_id")
            if topic_id:
                found_topic_ids.add(topic_id)
            
            # Check section title (normalized)
            title = section.get("title", "").lower()
            if title:
                found_topic_titles.add(title)
        
        # Find missing topics (by ID or title match)
        missing_topics = []
        for topic in chunker_topics:
            topic_id = topic.get("topic_id")
            title = topic.get("title", "")
            
            # Consider topic covered if either ID or title matches
            id_found = topic_id in found_topic_ids
            title_found = title.lower() in found_topic_titles
            
            if not (id_found or title_found):
                missing_topics.append({
                    "topic_id": topic_id,
                    "title": title
                })
        
        status = "passed" if not missing_topics else "failed"
        
        result = {
            "status": status,
            "total_topics": len(chunker_topics),
            "covered_topics": len(chunker_topics) - len(missing_topics),
            "missing_topics": missing_topics
        }
        
        if missing_topics:
            logger.warning(f"Missing topics: {[t['title'] for t in missing_topics]}")
        
        return result
    
    def _validate_key_terms(self, presentation: Dict, chunker_data: Dict) -> Dict:
        """
        Validate that key terms from chunker appear in presentation narration.
        
        Returns:
            {
                "status": "passed" | "failed",
                "total_terms": int,
                "found_terms": int,
                "missing_terms": [str]
            }
        """
        logger.info("[KeyTerms] Checking key term coverage...")
        
        # Extract key terms from chunker topics
        all_key_terms = set()
        for topic in chunker_data.get("topics", []):
            terms = topic.get("key_terms", [])
            all_key_terms.update([term.lower() for term in terms])
        
        if not all_key_terms:
            return {
                "status": "passed",
                "total_terms": 0,
                "found_terms": 0,
                "missing_terms": [],
                "note": "No key terms in chunker output"
            }
        
        # Build full narration text from presentation
        narration_text = ""
        for section in presentation.get("sections", []):
            for segment in section.get("narration", {}).get("segments", []):
                text = segment.get("text", "")
                narration_text += f" {text.lower()}"
        
        # Find which terms are present
        found_terms = set()
        missing_terms = []
        
        for term in all_key_terms:
            if term in narration_text:
                found_terms.add(term)
            else:
                missing_terms.append(term)
        
        # Allow some tolerance - if 80%+ of key terms found, pass
        coverage_percent = (len(found_terms) / len(all_key_terms) * 100) if all_key_terms else 100
        status = "passed" if coverage_percent >= 80 else "failed"
        
        result = {
            "status": status,
            "total_terms": len(all_key_terms),
            "found_terms": len(found_terms),
            "missing_terms": sorted(missing_terms),
            "coverage_percent": round(coverage_percent, 1)
        }
        
        if missing_terms and status == "failed":
            logger.warning(f"Missing key terms: {missing_terms[:5]}...")  # Show first 5
        
        return result
    
    def _validate_content_volume(self, presentation: Dict, source_markdown: str) -> Dict:
        """
        Validate that total narration word count is similar to source markdown.
        
        Returns:
            {
                "status": "passed" | "failed",
                "source_word_count": int,
                "presentation_word_count": int,
                "coverage_percent": float
            }
        """
        logger.info("[ContentVolume] Checking word count coverage...")
        
        # Count words in source markdown (exclude markdown syntax)
        import re
        # Remove markdown links, images, code blocks
        cleaned_source = re.sub(r'!\[.*?\]\(.*?\)', '', source_markdown)  # Images
        cleaned_source = re.sub(r'\[.*?\]\(.*?\)', '', cleaned_source)  # Links
        cleaned_source = re.sub(r'```.*?```', '', cleaned_source, flags=re.DOTALL)  # Code blocks
        cleaned_source = re.sub(r'`.*?`', '', cleaned_source)  # Inline code
        cleaned_source = re.sub(r'#{1,6}\s+', '', cleaned_source)  # Headers
        
        source_word_count = len(cleaned_source.split())
        
        # Count words in presentation narration
        narration_text = ""
        for section in presentation.get("sections", []):
            for segment in section.get("narration", {}).get("segments", []):
                text = segment.get("text", "")
                narration_text += f" {text}"
        
        presentation_word_count = len(narration_text.split())
        
        # Calculate coverage percentage
        if source_word_count > 0:
            coverage_percent = (presentation_word_count / source_word_count) * 100
        else:
            coverage_percent = 100
        
        # Status: Pass if within tolerance range
        min_acceptable = 100 - self.tolerance_percent
        max_acceptable = 100 + self.tolerance_percent
        
        status = "passed" if min_acceptable <= coverage_percent <= max_acceptable else "failed"
        
        result = {
            "status": status,
            "source_word_count": source_word_count,
            "presentation_word_count": presentation_word_count,
            "coverage_percent": round(coverage_percent, 1),
            "tolerance_range": f"{min_acceptable}% - {max_acceptable}%"
        }
        
        if status == "failed":
            logger.warning(f"Word count mismatch: {coverage_percent:.1f}% coverage (target: {min_acceptable}-{max_acceptable}%)")
        
        return result
    
    def _build_retry_prompt(self, checks: Dict) -> str:
        """
        Build enhanced prompt for Director LLM retry with missing content details.
        
        Args:
            checks: Dictionary of validation check results
            
        Returns:
            Formatted retry prompt text
        """
        prompt_lines = ["CRITICAL CONTENT VALIDATION FEEDBACK:", ""]
        prompt_lines.append("Your previous generation was missing the following content from the source markdown:")
        prompt_lines.append("")
        
        # Image coverage issues
        image_check = checks.get("image_coverage", {})
        missing_images = image_check.get("missing_images", [])
        if missing_images:
            prompt_lines.append("❌ MISSING IMAGE REFERENCES:")
            for img in missing_images:
                prompt_lines.append(f"   - {img}")
            prompt_lines.append("")
        
        # Topic coverage issues
        topic_check = checks.get("topic_coverage", {})
        missing_topics = topic_check.get("missing_topics", [])
        if missing_topics:
            prompt_lines.append("❌ MISSING TOPICS (You MUST create sections for these):")
            for topic in missing_topics:
                topic_id = topic.get("topic_id", "unknown")
                title = topic.get("title", "Unknown")
                prompt_lines.append(f"   - Topic ID: {topic_id}, Title: \"{title}\"")
            prompt_lines.append("")
        
        # Key terms issues
        terms_check = checks.get("key_terms", {})
        missing_terms = terms_check.get("missing_terms", [])
        if missing_terms and terms_check.get("status") == "failed":
            prompt_lines.append("❌ MISSING KEY TERMS (Include these in narration):")
            # Show up to 10 terms
            for term in missing_terms[:10]:
                prompt_lines.append(f"   - {term}")
            if len(missing_terms) > 10:
                prompt_lines.append(f"   ... and {len(missing_terms) - 10} more")
            prompt_lines.append("")
        
        # Content volume issues
        volume_check = checks.get("content_volume", {})
        if volume_check.get("status") == "failed":
            coverage = volume_check.get("coverage_percent", 0)
            source_words = volume_check.get("source_word_count", 0)
            pres_words = volume_check.get("presentation_word_count", 0)
            
            prompt_lines.append("❌ CONTENT VOLUME MISMATCH:")
            prompt_lines.append(f"   - Source markdown: {source_words} words")
            prompt_lines.append(f"   - Your generation: {pres_words} words")
            prompt_lines.append(f"   - Coverage: {coverage:.1f}% (target: 80-120%)")
            
            if coverage < 80:
                prompt_lines.append("   - ACTION: You need to include MORE content from the source")
            else:
                prompt_lines.append("   - ACTION: You added too much extra content, stick closer to source")
            prompt_lines.append("")
        
        prompt_lines.append("=" * 80)
        prompt_lines.append("YOU MUST FIX ALL OF THE ABOVE ISSUES IN THIS REGENERATION.")
        prompt_lines.append("=" * 80)
        
        return "\n".join(prompt_lines)


# Convenience function for pipeline integration
def validate_content_completeness(
    presentation: Dict,
    job_dir: str,
    source_markdown: str
) -> Dict:
    """
    Convenience function to validate content completeness.
    
    Args:
        presentation: presentation.json dict
        job_dir: Job directory path (e.g., "jobs/abc123")
        source_markdown: Original markdown content
        
    Returns:
        Validation result dict
    """
    validator = ContentCompletenessValidator()
    
    chunker_path = Path(job_dir) / "artifacts" / "01_chunker.json"
    images_dir = Path(job_dir) / "images"
    
    return validator.validate(
        presentation=presentation,
        chunker_output_path=str(chunker_path),
        images_dir=str(images_dir),
        source_markdown=source_markdown
    )
