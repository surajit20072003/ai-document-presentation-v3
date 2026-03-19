"""
Smart Chunker v1.5 - Pass 0: Topic Extraction with Block Type Detection (ISS-160)

Extracts logical topic blocks from markdown with metadata for downstream Directors.
Uses Gemini 2.5 Pro with structured output (JSON schema enforcement).

ISS-160: Now detects block_type (paragraph, unordered_list, ordered_list, formula, blockquote)
and preserves verbatim_content from source for display fidelity.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from openai import OpenAI

from core.analytics import AnalyticsTracker
from core.json_repair import repair_and_parse_json, validate_json_structure
from core.llm_config import get_model_name, get_fallback_model_name

logger = logging.getLogger(__name__)

MODEL = get_model_name()
PROMPTS_DIR = Path(__file__).parent / "prompts"

MAX_STRUCTURAL_RETRIES = (
    3  # ISS-201: Increased from 2 to give LLM more chances to self-correct
)

SMART_CHUNKER_SCHEMA = {
    "type": "object",
    "properties": {
        "source_topic": {
            "type": "string",
            "description": "The main subject matter of the provided text",
        },
        "content_density_analysis": {
            "type": "object",
            "description": "Analysis of content density to guide section planning",
            "properties": {
                "total_concepts": {"type": "integer"},
                "formula_count": {"type": "integer"},
                "table_count": {"type": "integer"},
                "image_count": {"type": "integer"},
                "qa_pair_count": {"type": "integer"},
                "density_rating": {
                    "type": "string",
                    "enum": ["light", "medium", "heavy"],
                },
                "recommended_content_sections": {"type": "integer"},
                "reasoning": {"type": "string"},
            },
            "required": [
                "total_concepts",
                "recommended_content_sections",
                "density_rating",
            ],
        },
        "topics": {
            "type": "array",
            "description": "List of logical sub-topics extracted from the text",
            "items": {
                "type": "object",
                "properties": {
                    "topic_id": {"type": "string"},
                    "title": {"type": "string"},
                    "concept_type": {
                        "type": "string",
                        "enum": [
                            "process",
                            "definition",
                            "example",
                            "formula",
                            "theory",
                            "fact",
                        ],
                    },
                    "source_blocks": {"type": "array", "items": {"type": "integer"}},
                    "key_terms": {"type": "array", "items": {"type": "string"}},
                    "has_formula": {"type": "boolean"},
                    "suggested_renderer": {
                        "type": "string",
                        "enum": ["none", "manim", "video"],
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["light", "medium", "heavy"],
                    },
                    "concept_count": {"type": "integer"},
                },
                "required": [
                    "topic_id",
                    "title",
                    "concept_type",
                    "source_blocks",
                    "suggested_renderer",
                ],
            },
        },
        "topic_grouping_hints": {
            "type": "array",
            "description": "Recommended groupings of topics into content sections",
            "items": {
                "type": "object",
                "properties": {
                    "content_section": {"type": "integer"},
                    "topic_ids": {"type": "array", "items": {"type": "string"}},
                    "total_concepts": {"type": "integer"},
                },
                "required": ["content_section", "topic_ids"],
            },
        },
        "quiz_questions": {
            "type": "array",
            "description": "Quiz questions extracted from PDF (optional, empty if none found)",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "string"},
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "source_block": {"type": "integer"},
                },
                "required": ["question_id", "question", "answer"],
            },
        },
    },
    "required": [
        "source_topic",
        "topics",
        "content_density_analysis",
        "topic_grouping_hints",
    ],
}


def detect_block_type(line: str) -> str:
    """
    Detect the block type from a markdown line.
    ISS-160: Source fidelity - detect exact formatting.
    ISS-209: Added table detection
    ISS-210: Added image detection

    Returns:
        One of: paragraph, unordered_list, ordered_list, formula, blockquote, table, image
    """
    stripped = line.strip()

    if not stripped:
        return "paragraph"  # Empty lines treated as paragraph breaks

    # ISS-210: Image detection - ![alt](url) or ![alt][ref]
    if re.match(r"^!\[.*?\]\(.*?\)", stripped) or re.match(
        r"^!\[.*?\]\[.*?\]", stripped
    ):
        return "image"

    # ISS-209: Table detection - lines starting with | or containing | separators
    if stripped.startswith("|") or re.match(r"^.+\|.+$", stripped):
        # Additional check: must have at least 2 pipe characters for a valid table row
        if stripped.count("|") >= 2:
            return "table"

    # Table separator line: |---|---|
    if re.match(r"^\|?\s*[-:]+\s*\|", stripped):
        return "table"

    # Ordered list: starts with digit + period + space
    if re.match(r"^\d+\.\s", stripped):
        return "ordered_list"

    # Unordered list: starts with -, *, + followed by space
    if re.match(r"^[-*+]\s", stripped):
        return "unordered_list"

    # Block formula: contains $$...$$ (display math) - standalone formula block
    if "$$" in stripped:
        return "formula"

    # ISS-160 FIX: Only return "formula" for PURE formula lines (single $...$, nothing else)
    # Lines with inline math like "The ratio $\sin\theta$ is" are PARAGRAPHS
    inline_math_match = re.match(r"^\$[^$]+\$\s*$", stripped)
    if inline_math_match:
        return "formula"  # Line is ONLY a formula

    # Blockquote: starts with >
    if stripped.startswith(">"):
        return "blockquote"

    # Heading is treated as paragraph for display
    if stripped.startswith("#"):
        return "paragraph"

    # ISS-160: Paragraphs with inline math stay as paragraphs - has_inline_latex tracks the math
    return "paragraph"


def has_inline_latex(text: str) -> bool:
    """Check if text contains inline LaTeX notation."""
    # Match $...$ but not $$...$$
    inline_pattern = r"(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)"
    return bool(re.search(inline_pattern, text))


def parse_content_blocks(markdown_content: str) -> List[Dict]:
    """
    Parse markdown content into content blocks with type detection.
    ISS-160: Preserves verbatim content for source fidelity.

    Returns:
        List of content blocks with block_id, block_type, verbatim_content, etc.
    """
    blocks = []
    lines = markdown_content.split("\n")

    current_block = []
    current_type = None
    block_id = 1
    start_line = 1

    def flush_block():
        nonlocal block_id, current_block, current_type, start_line
        if current_block:
            content = "\n".join(current_block)
            block = {
                "block_id": block_id,
                "block_type": current_type or "paragraph",
                "verbatim_content": content,
                "source_line": start_line,
                "has_inline_latex": has_inline_latex(content),
            }

            # For list types, extract items
            if current_type == "unordered_list":
                items = [
                    re.sub(r"^[-*+]\s*", "", line.strip())
                    for line in current_block
                    if re.match(r"^[-*+]\s", line.strip())
                ]
                block["items"] = items
            elif current_type == "ordered_list":
                items = [
                    re.sub(r"^\d+\.\s*", "", line.strip())
                    for line in current_block
                    if re.match(r"^\d+\.\s", line.strip())
                ]
                block["items"] = items

            # ISS-209: Parse table structure
            elif current_type == "table":
                rows = []
                for line in current_block:
                    # Skip separator lines (|---|---|)
                    if re.match(r"^\|?\s*[-:]+\s*\|", line.strip()):
                        continue
                    # Parse cells from pipe-separated values
                    cells = [
                        cell.strip() for cell in line.strip().strip("|").split("|")
                    ]
                    if cells and any(cell for cell in cells):
                        rows.append(cells)
                block["table_rows"] = rows
                if rows:
                    block["table_headers"] = rows[0]
                    block["table_data"] = rows[1:] if len(rows) > 1 else []

            # ISS-210: Parse image references
            elif current_type == "image":
                # Extract image URL and alt text from ![alt](url) format
                match = re.search(r"!\[(.*?)\]\((.*?)\)", content)
                if match:
                    block["image_alt"] = match.group(1)
                    block["image_url"] = match.group(2)
                # Also try ![alt][ref] format
                ref_match = re.search(r"!\[(.*?)\]\[(.*?)\]", content)
                if ref_match:
                    block["image_alt"] = ref_match.group(1)
                    block["image_ref"] = ref_match.group(2)

            blocks.append(block)
            block_id += 1
        current_block = []
        current_type = None

    for i, line in enumerate(lines, 1):
        if not line.strip():
            # Empty line - flush current block
            flush_block()
            start_line = i + 1
            continue

        line_type = detect_block_type(line)

        # If type changes, flush and start new block
        if current_type is not None and line_type != current_type:
            flush_block()
            start_line = i

        if current_type is None:
            current_type = line_type
            start_line = i

        current_block.append(line)

    # Flush final block
    flush_block()

    return blocks


def load_prompt(name: str) -> str:
    """Load a prompt file."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r") as f:
        return f.read()


def call_smart_chunker(
    markdown_content: str,
    subject: str,
    tracker: Optional[AnalyticsTracker] = None,
    max_retries: int = MAX_STRUCTURAL_RETRIES,
) -> Dict:
    """
    PASS 0: Extract logical topics from markdown.
    Uses Gemini 2.5 Pro with JSON schema enforcement.

    Args:
        markdown_content: Raw markdown content from document
        subject: Subject area (e.g., "Biology", "Physics")
        tracker: Analytics tracker for cost/time logging
        max_retries: Maximum structural retries (default 2)

    Returns:
        Dict with source_topic and topics array

    Raises:
        ChunkerError: If chunking fails after all retries
    """
    logger.info(f"[Smart Chunker] Starting topic extraction for {subject}")

    system_prompt = load_prompt("smart_chunker_system_v1.5")
    user_prompt_template = load_prompt("smart_chunker_user_v1.5")

    # ISS-FIX: Initialize client here to ensure env vars are loaded
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("[Smart Chunker] OPENROUTER_API_KEY is missing or empty!")
        raise ChunkerError("OPENROUTER_API_KEY is not set.")

    logger.info(
        f"[Smart Chunker] Using API Key: {api_key[:5]}... (len={len(api_key)}) for model {MODEL}"
    )

    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    numbered_content = _add_block_numbers(markdown_content)

    user_prompt = user_prompt_template.format(
        subject=subject, markdown_content=numbered_content
    )

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if tracker:
                tracker.start_phase("smart_chunker", MODEL)

            # ISS-214: Removed max_tokens limit - let API use natural limits
            # ISS-Fallback: Implement fallback model logic
            current_model = MODEL
            try:
                response = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
            except Exception as e:
                # Check if it's an API error that warrants fallback
                error_str = str(e).lower()
                is_api_error = any(
                    code in error_str
                    for code in [
                        "401",
                        "404",
                        "429",
                        "500",
                        "502",
                        "503",
                        "rate limit",
                        "not found",
                        "unauthorized",
                    ]
                )

                if is_api_error:
                    fallback_model = get_fallback_model_name()
                    if fallback_model and fallback_model != current_model:
                        logger.warning(
                            f"[Smart Chunker] Primary model {current_model} failed ({e}). Switching to fallback: {fallback_model}"
                        )
                        current_model = fallback_model
                        response = client.chat.completions.create(
                            model=current_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.2,
                            response_format={"type": "json_object"},
                        )
                    else:
                        raise e
                else:
                    raise e

            raw_response = response.choices[0].message.content or ""

            if not raw_response:
                raise ChunkerError("Empty response from LLM")

            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            if tracker:
                tracker.end_phase("smart_chunker", input_tokens, output_tokens)

            result = repair_and_parse_json(raw_response)

            errors = _validate_chunker_output(result)
            if errors:
                raise ChunkerValidationError(errors)

            # ISS-160: Add content_blocks with block_type detection
            content_blocks = parse_content_blocks(markdown_content)
            result["content_blocks"] = content_blocks

            # ISS-ValidationMetadata: Add validation metadata for Content Completeness Validator
            topics = result.get("topics", [])
            all_key_terms = []
            for topic in topics:
                all_key_terms.extend(topic.get("key_terms", []))

            result["validation_metadata"] = {
                "total_topics": len(topics),
                "topic_ids": [t.get("topic_id") for t in topics if t.get("topic_id")],
                "topic_titles": [t.get("title") for t in topics if t.get("title")],
                "all_key_terms": list(set(all_key_terms)),  # Unique terms
                "source_word_count": len(markdown_content.split()),
                "total_images": len(
                    [b for b in content_blocks if b.get("block_type") == "image"]
                ),
                "total_formulas": len(
                    [b for b in content_blocks if b.get("block_type") == "formula"]
                ),
                "total_tables": len(
                    [b for b in content_blocks if b.get("block_type") == "table"]
                ),
            }

            logger.info(
                f"[Smart Chunker] Successfully extracted {len(result.get('topics', []))} topics, {len(content_blocks)} content blocks"
            )
            return result

        except (json.JSONDecodeError, ChunkerValidationError) as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"[Smart Chunker] Retry {attempt + 1}/{max_retries}: {e}"
                )
                user_prompt = _get_retry_prompt(user_prompt, str(e))
            else:
                logger.error(f"[Smart Chunker] Failed after {max_retries} retries: {e}")

        except Exception as e:
            logger.error(f"[Smart Chunker] Unexpected error: {e}")
            raise ChunkerError(f"Unexpected error in Smart Chunker: {e}")

    raise ChunkerError(
        f"Smart Chunker failed after {max_retries} retries: {last_error}"
    )


def _add_block_numbers(content: str) -> str:
    """Add block numbers to markdown content for reference."""
    lines = content.split("\n")
    numbered = []
    block_num = 0
    in_block = False

    for line in lines:
        stripped = line.strip()

        if (
            stripped.startswith("#")
            or stripped.startswith("##")
            or stripped.startswith("###")
        ):
            block_num += 1
            numbered.append(f"[BLOCK {block_num}]")
            numbered.append(line)
            in_block = True
        elif stripped and not in_block:
            block_num += 1
            numbered.append(f"[BLOCK {block_num}]")
            numbered.append(line)
            in_block = True
        elif stripped:
            numbered.append(line)
        else:
            numbered.append(line)
            in_block = False

    return "\n".join(numbered)


def _validate_chunker_output(data: Dict) -> List[str]:
    """Validate chunker output structure and content."""
    errors = []

    missing = validate_json_structure(data, ["source_topic", "topics"])
    if missing:
        errors.append(f"Missing required fields: {missing}")

    topics = data.get("topics", [])
    if not topics:
        errors.append("topics array is empty")

    for i, topic in enumerate(topics):
        topic_errors = _validate_topic(topic, i)
        errors.extend(topic_errors)

    return errors


def _validate_topic(topic: Dict, index: int) -> List[str]:
    """Validate a single topic entry."""
    errors = []
    prefix = f"topics[{index}]"

    required = [
        "topic_id",
        "title",
        "concept_type",
        "source_blocks",
        "suggested_renderer",
    ]
    for field in required:
        if field not in topic:
            errors.append(f"{prefix}: missing required field '{field}'")

    valid_types = ["process", "definition", "example", "formula", "theory", "fact"]
    if topic.get("concept_type") and topic["concept_type"] not in valid_types:
        errors.append(f"{prefix}: invalid concept_type '{topic['concept_type']}'")

    # ISS-201 FIX: Accept 'none' as valid renderer (matches prompt guidance)
    # Also accept null/None/empty string which should be treated as 'none'
    valid_renderers = [
        "remotion",
        "manim",
        "video",
        "none",
        "wan",
        "wan_video",
        "image_to_video",
        "infographic",
        "image",
        "threejs",
    ]
    renderer_value = topic.get("suggested_renderer")

    # Normalize null/empty to 'none' (don't fail on these)
    if renderer_value is None or renderer_value == "" or renderer_value == "null":
        pass  # Valid - no renderer needed
    elif renderer_value and renderer_value.lower() not in [
        r.lower() for r in valid_renderers
    ]:
        errors.append(f"{prefix}: invalid suggested_renderer '{renderer_value}'")

    return errors


def _get_retry_prompt(original_prompt: str, error_message: str) -> str:
    """Generate retry prompt with specific error feedback."""
    retry_addition = f"""

---
RETRY REQUIRED: Your previous response had the following errors:
{error_message}

Please fix these issues and output valid JSON matching the required schema.
Ensure all required fields are present: source_topic, topics array with topic_id, title, concept_type, source_blocks, suggested_renderer.

VALID VALUES:
- concept_type: "process" | "definition" | "example" | "formula" | "theory" | "fact"
- suggested_renderer: "manim" | "video" | "none" (use "none" for text-only sections like intro/summary)
---

"""
    return original_prompt + retry_addition


class ChunkerError(Exception):
    """Error raised when Smart Chunker fails."""

    pass


class ChunkerValidationError(Exception):
    """Error raised when Smart Chunker output fails validation."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation errors: {', '.join(errors)}")
