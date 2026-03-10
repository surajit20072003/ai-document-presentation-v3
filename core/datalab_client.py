import os
import time
import requests
from pathlib import Path
from typing import Dict, Any, Tuple

DATALAB_API_KEY = os.environ.get("DATALAB_API_KEY", "")
DATALAB_API_URL = "https://api.datalab.to/api/v1/marker"
MIN_MARKDOWN_LENGTH = 100
MAX_POLL_TIME = 300
POLL_INTERVAL = 3

# ISS-206: Datalab supports these file types
SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.odt'}


class DatalabConversionError(Exception):
    """Raised when Datalab PDF conversion fails - NO fallback allowed."""
    pass


class ConversionResult:
    """ISS-207: Result object with markdown and metadata (page_count, images, etc)."""
    def __init__(self, markdown: str, page_count: int = 0, metadata: Dict[str, Any] = None, images: Dict[str, str] = None):
        self.markdown = markdown
        self.page_count = page_count
        self.metadata = metadata or {}
        self.images = images or {}  # Dict of filename -> base64 data
    
    def __str__(self):
        return self.markdown


def is_supported_file(filename: str) -> bool:
    """ISS-206: Check if file extension is supported by Datalab."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """ISS-206: Get MIME type for supported file types."""
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.odt': 'application/vnd.oasis.opendocument.text'
    }
    return mime_types.get(ext, 'application/octet-stream')


def document_to_markdown(file_path: str) -> ConversionResult:
    """ISS-206: Convert PDF/DOC/DOCX/ODT to markdown using Datalab API.
    
    FAIL-FAST: No fallback to local extraction. Raises DatalabConversionError if:
    - DATALAB_API_KEY not configured
    - File type not supported
    - API request fails
    - Returned markdown is less than MIN_MARKDOWN_LENGTH chars
    
    Returns:
        ConversionResult with markdown text and metadata (page_count, etc)
    """
    if not DATALAB_API_KEY:
        raise DatalabConversionError(
            "DATALAB_API_KEY not configured. Document conversion requires Datalab API."
        )
    
    if not is_supported_file(file_path):
        ext = Path(file_path).suffix
        raise DatalabConversionError(
            f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    result = _convert_with_datalab(file_path)
    
    if len(result.markdown) < MIN_MARKDOWN_LENGTH:
        raise DatalabConversionError(
            f"Datalab returned insufficient content ({len(result.markdown)} chars). "
            f"Minimum required: {MIN_MARKDOWN_LENGTH} chars. "
            "Document may be image-only or corrupted."
        )
    
    return result


def pdf_to_markdown(pdf_path: str) -> str:
    """Legacy function - Convert PDF to markdown using Datalab API.
    
    FAIL-FAST: No fallback to local extraction. Raises DatalabConversionError if:
    - DATALAB_API_KEY not configured
    - API request fails
    - Returned markdown is less than MIN_MARKDOWN_LENGTH chars
    """
    result = document_to_markdown(pdf_path)
    return result.markdown

def _convert_with_datalab(file_path: str) -> ConversionResult:
    """ISS-206/207: Call Datalab API to convert PDF/DOC/DOCX/ODT to markdown.
    
    Datalab uses async processing - submit file, then poll for results.
    Returns ConversionResult with markdown and page_count.
    """
    try:
        filename = Path(file_path).name
        mime_type = get_mime_type(file_path)
        
        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            headers = {"X-Api-Key": DATALAB_API_KEY}
            
            print(f"[Datalab] Submitting document: {file_path} (type: {mime_type})")
            response = requests.post(
                DATALAB_API_URL,
                files=files,
                headers=headers,
                data={"output_format": "markdown"},
                timeout=120
            )
            
            if response.status_code != 200:
                raise DatalabConversionError(
                    f"Datalab API error: {response.status_code} - {response.text[:500]}"
                )
            
            result = response.json()
            
            # ISS-207: Extract page_count from response
            page_count = result.get("page_count", 0)
            
            # Extract images dict from response (base64 encoded)
            images = result.get("images", {})
            if images:
                print(f"[Datalab] Found {len(images)} images in response")
            
            if result.get("markdown"):
                return ConversionResult(
                    markdown=result["markdown"],
                    page_count=page_count,
                    metadata={"source": "immediate"},
                    images=images
                )
            if result.get("text"):
                return ConversionResult(
                    markdown=result["text"],
                    page_count=page_count,
                    metadata={"source": "immediate_text"},
                    images=images
                )
            
            check_url = result.get("request_check_url")
            if not check_url:
                raise DatalabConversionError(
                    f"Datalab returned no markdown and no check URL: {result}"
                )
            
            print(f"[Datalab] Polling for results: {check_url}")
            return _poll_for_result(check_url)
            
    except requests.exceptions.RequestException as e:
        raise DatalabConversionError(f"Datalab API request failed: {e}")


def _poll_for_result(check_url: str) -> ConversionResult:
    """ISS-207: Poll Datalab API until conversion is complete. Returns ConversionResult."""
    elapsed = 0
    
    while elapsed < MAX_POLL_TIME:
        try:
            response = requests.get(
                check_url,
                headers={"X-Api-Key": DATALAB_API_KEY},
                timeout=30
            )
            
            if response.status_code != 200:
                raise DatalabConversionError(
                    f"Datalab poll failed: {response.status_code} - {response.text[:200]}"
                )
            
            result = response.json()
            status = result.get("status", "unknown")
            page_count = result.get("page_count", 0)
            print(f"[Datalab] Status: {status}, Pages: {page_count} (elapsed: {elapsed}s)")
            
            if status == "complete":
                markdown = result.get("markdown", result.get("text", ""))
                images = result.get("images", {})
                if images:
                    print(f"[Datalab] Found {len(images)} images in polled response")
                if markdown:
                    print(f"[Datalab] SUCCESS: {len(markdown)} chars, {page_count} pages, {len(images)} images")
                    return ConversionResult(
                        markdown=markdown,
                        page_count=page_count,
                        images=images,
                        metadata={"source": "polled"}
                    )
                raise DatalabConversionError("Datalab completed but returned no content")
            
            if status == "error" or status == "failed":
                error_msg = result.get("error", "Unknown error")
                raise DatalabConversionError(f"Datalab conversion failed: {error_msg}")
            
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            
        except requests.exceptions.RequestException as e:
            raise DatalabConversionError(f"Datalab poll request failed: {e}")
    
    raise DatalabConversionError(f"Datalab conversion timed out after {MAX_POLL_TIME}s")
