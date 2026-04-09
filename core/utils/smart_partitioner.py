import logging
import json
import re
import os
from typing import List, Dict, Optional
from core.unified_content_generator import extract_json_from_response, GeneratorConfig
from core.llm_routing import call_llm_routed

logger = logging.getLogger(__name__)

class SmartPartitioner:
    def __init__(self, config: GeneratorConfig, llm_routing: Optional[dict] = None):
        self.config = config
        self.llm_routing = llm_routing or {}
        
    def partition_markdown(self, markdown_content: str, subject: str, grade: str) -> List[Dict]:
        """
        Uses LLM to plan the cuts, then physically slices the markdown.
        Returns a list of dicts: [{'id': 1, 'content': '...', 'title': '...'}, ...]
        """
        
        # 1. Get the Plan from LLM
        logger.info("SmartPartitioner: Requesting partition plan from LLM...")
        chunks_plan = self._get_partition_plan(markdown_content)

        # 2. Slice the content
        logger.info(f"SmartPartitioner: Received plan with {len(chunks_plan)} chunks. Slicing...")
        final_chunks = []
        
        for plan in chunks_plan:
            chunk_content = self._slice_content(
                markdown_content, 
                plan.get("start_header"), 
                plan.get("end_header")
            )
            
            if chunk_content.strip():
                final_chunks.append({
                    "chunk_id": plan.get("chunk_id"),
                    "title": plan.get("approx_title", f"Part {plan.get('chunk_id')}"),
                    "content": chunk_content,
                    "plan_reasoning": plan.get("reasoning", "")
                })
                
        return final_chunks

    def _get_partition_plan(self, markdown_content: str) -> List[Dict]:
        """Calls LLM to define cut points."""
        try:
            with open("core/prompts/planner_chunker_prompt.txt", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except Exception:
            # Fallback inline if file missing
            system_prompt = "You are a Document Architect. Return JSON {chunks: [...]} splitting MD by headers."

        user_prompt = f"DOCUMENT LENGTH: {len(markdown_content)} chars.\n\nCONTENT:\n{markdown_content}" 
        # Note: Truncate context if huge, but typically we want full doc structure. 
        # For 100k+ chars, we might need a map-reduce, but for <30k chars 1 call is fine.

        # Use Flash for Chunker (Fast & Cheap)
        import copy
        flash_config = copy.copy(self.config)
        flash_config.model = os.environ.get("CHUNKER_MODEL", "google/gemini-2.0-flash-exp")
        
        chunk_hint = "\nIMPORTANT: The document is large. Aim for chunks of roughly 10,000 to 15,000 characters each to allow parallel processing." if len(markdown_content) > 15000 else ""
        user_prompt += chunk_hint
        
        response, _ = call_llm_routed(system_prompt, user_prompt, flash_config, component="chunker", routing=self.llm_routing)
        data = extract_json_from_response(response)
        
        # [PHASE 1 DEBUG]
        print(f"\n[PHASE 1 DEBUG] SmartPartitioner Plan ({len(markdown_content)} chars):")
        print(json.dumps(data, indent=2))
        print(f"[PHASE 1 DEBUG] --------------------------------------------------\n")
        
        return data.get("chunks", [])

    def _slice_content(self, full_text: str, start_header: str, end_header: str) -> str:
        """extract text between two headers."""
        if not start_header:
            return ""
            
        # Find start
        start_idx = full_text.find(start_header)
        if start_idx == -1:
            # Graceful degradation: Try looser match or regex? 
            # For now, strict match. If LLM hallucinates header, we might skip.
            # IMPROVEMENT: Normalized comparison.
            logger.warning(f"Partitioner: Could not find start header '{start_header}'")
            return ""

        # Find end
        if end_header == "END_OF_DOCUMENT":
            return full_text[start_idx:]
            
        end_idx = full_text.find(end_header, start_idx + len(start_header))
        
        if end_idx == -1:
            logger.warning(f"Partitioner: Could not find end header '{end_header}'. Taking rest of doc.")
            return full_text[start_idx:]
            
        return full_text[start_idx:end_idx]

    def _fallback_split(self, text: str) -> List[Dict]:
        """Blind split by ## if LLM fails."""
        # Simple regex split
        parts = re.split(r'\n## ', text)
        chunks = []
        for i, p in enumerate(parts):
            if p.strip():
                chunks.append({
                    "chunk_id": i+1, 
                    "title": f"Section {i+1}", 
                    "content": "## " + p if i > 0 else p
                })
        return chunks
