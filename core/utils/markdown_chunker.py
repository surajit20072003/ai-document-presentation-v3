import re
from typing import List

class MarkdownChunker:
    """
    Splits markdown into logical chunks while preserving structure (headings, tables, etc.).
    Designed for processing large documents via LLM in a loop.
    """
    
    def __init__(self, target_chars: int = 10000, overlap_chars: int = 500):
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

    def chunk(self, markdown: str) -> List[str]:
        if not markdown or len(markdown) <= self.target_chars:
            return [markdown]

        # 1. Split by headings (first priority)
        # We split by H1, H2, or H3 headings
        lines = markdown.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            if re.match(r'^#{1,3}\s', line):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))

        # 2. Group sections into chunks
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # If a single section is larger than target, we'll need to split it by paragraphs
            if len(section) > self.target_chars:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split large section by paragraphs
                sub_chunks = self._split_by_paragraphs(section)
                chunks.extend(sub_chunks)
            else:
                if len(current_chunk) + len(section) > self.target_chars and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = section
                else:
                    if current_chunk:
                        current_chunk += "\n\n" + section
                    else:
                        current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Fallback splitter for massive sections without enough headings."""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for p in paragraphs:
            if len(current_chunk) + len(p) > self.target_chars and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = p
            else:
                if current_chunk:
                    current_chunk += "\n\n" + p
                else:
                    current_chunk = p
                    
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

def smart_split(markdown: str, target_chars: int = 10000) -> List[str]:
    chunker = MarkdownChunker(target_chars=target_chars)
    return chunker.chunk(markdown)
