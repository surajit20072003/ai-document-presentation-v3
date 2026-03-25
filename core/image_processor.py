import os
import re
import base64
from pathlib import Path
from PIL import Image
from io import BytesIO

try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("[ImageProcessor] rembg not available - will use basic processing")


def extract_images_from_markdown(md_content: str, output_dir: str) -> dict:
    """
    Extract base64 images from markdown content, save them with green background.
    Returns mapping: {"IMAGE_1": "filename.png", ...}
    """
    os.makedirs(output_dir, exist_ok=True)
    
    base64_pattern = r'!\[([^\]]*)\]\(data:image/(png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=]+)\)'
    
    matches = re.findall(base64_pattern, md_content)
    
    images_mapping = {}
    image_counter = 0
    
    for alt_text, img_format, base64_data in matches:
        image_counter += 1
        img_key = f"IMAGE_{image_counter}"
        
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', alt_text or f"image_{image_counter}")
        filename = f"{safe_name}.png"
        filepath = os.path.join(output_dir, filename)
        
        try:
            img_bytes = base64.b64decode(base64_data)
            img = Image.open(BytesIO(img_bytes))
            
            processed_img = apply_green_background(img)
            
            processed_img.save(filepath, 'PNG')
            
            images_mapping[img_key] = {
                'filename': filename,
                'alt_text': alt_text,
                'path': filepath,
                'width': processed_img.width,
                'height': processed_img.height
            }
            
            print(f"[ImageProcessor] Saved {img_key}: {filename} ({processed_img.width}x{processed_img.height})")
            
        except Exception as e:
            print(f"[ImageProcessor] Error processing {img_key}: {e}")
            continue
    
    print(f"[ImageProcessor] Extracted {len(images_mapping)} images to {output_dir}")
    return images_mapping


def apply_green_background(img: Image.Image) -> Image.Image:
    """
    Process image for player display.
    
    CHANGED (2026-01-17): Removed rembg background removal as it was
    destroying diagram content. Images are now saved as-is without
    any destructive processing.
    
    If you need chroma key in the future, enable it explicitly via parameter.
    """
    # Just convert to RGB if needed (for PNG with transparency)
    if img.mode == 'RGBA':
        # Create white background for transparent images
        white_bg = Image.new('RGB', img.size, (255, 255, 255))
        white_bg.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        return white_bg
    elif img.mode != 'RGB':
        return img.convert('RGB')
    
    return img


def strip_base64_from_markdown(md_content: str) -> str:
    """
    Remove base64 image data from markdown, leaving only text.
    Replaces with IMAGE_X placeholders for LLM.
    """
    base64_pattern = r'!\[([^\]]*)\]\(data:image/[^;]+;base64,[A-Za-z0-9+/=]+\)'
    
    counter = [0]
    
    def replace_with_placeholder(match):
        counter[0] += 1
        alt_text = match.group(1) or f"image_{counter[0]}"
        return f"[IMAGE_{counter[0]}: {alt_text}]"
    
    clean_md = re.sub(base64_pattern, replace_with_placeholder, md_content)
    
    print(f"[ImageProcessor] Replaced {counter[0]} base64 images with placeholders")
    return clean_md


def create_image_list_for_llm(images_mapping: dict) -> str:
    """
    Create a text list of available images for LLM prompt.
    """
    if not images_mapping:
        return "No images available."
    
    lines = ["AVAILABLE IMAGES:"]
    for img_key, info in sorted(images_mapping.items()):
        alt = info.get('alt_text', 'No description')
        lines.append(f"  {img_key}: {alt} ({info['filename']})")
    
    return "\n".join(lines)


def save_datalab_images(images_dict: dict, output_dir: str, apply_green_screen: bool = True) -> dict:
    """
    Save base64 images from Datalab API response to disk.
    
    Args:
        images_dict: Dict of {filename: base64_data} from Datalab response
        output_dir: Directory to save images
        apply_green_screen: Whether to apply green screen for chroma key
    
    Returns:
        Dict mapping original filename to saved file info
    """
    os.makedirs(output_dir, exist_ok=True)
    
    saved_images = {}
    
    for filename, base64_data in images_dict.items():
        try:
            img_bytes = base64.b64decode(base64_data)
            img = Image.open(BytesIO(img_bytes))
            
            if apply_green_screen:
                processed_img = apply_green_background(img)
            else:
                processed_img = img.convert('RGB') if img.mode != 'RGB' else img
            
            output_filename = filename.replace('.jpg', '.png').replace('.jpeg', '.png')
            output_path = os.path.join(output_dir, output_filename)
            
            processed_img.save(output_path, 'PNG')
            
            # Key by OUTPUT filename (.png) — not original (.jpg) —
            # so that images_list passed to the Director LLM contains
            # the actual filenames on disk, preventing .jpg/.png mismatch.
            saved_images[output_filename] = {
                'filename': output_filename,
                'path': output_path,
                'width': processed_img.width,
                'height': processed_img.height
            }
            
            print(f"[ImageProcessor] Saved: {filename} -> {output_filename} ({processed_img.width}x{processed_img.height})")
            
        except Exception as e:
            print(f"[ImageProcessor] Error saving {filename}: {e}")
            continue
    
    print(f"[ImageProcessor] Saved {len(saved_images)}/{len(images_dict)} images to {output_dir}")
    return saved_images


def extract_image_refs_from_markdown(md_content: str) -> list:
    """
    Extract image references from markdown (Datalab format: filename_img.jpg).
    Returns list of image filenames referenced in the markdown.
    """
    pattern = r'!\[([^\]]*)\]\(([a-f0-9]+_img\.jpg)\)'
    matches = re.findall(pattern, md_content)
    
    image_refs = []
    for alt_text, filename in matches:
        image_refs.append({
            'filename': filename,
            'alt_text': alt_text
        })
    
    print(f"[ImageProcessor] Found {len(image_refs)} image references in markdown")
    return image_refs


if __name__ == "__main__":
    test_md = """
    # Test Document
    Here is an image: ![Test Diagram](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==)
    And some text.
    """
    
    clean = strip_base64_from_markdown(test_md)
    print("Clean markdown:", clean)
