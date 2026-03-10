#!/usr/bin/env python3
"""
Script to iterate through all jobs and compress avatar videos that are high quality (>480p).
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

# Configuration
JOBS_DIR = Path("/nvme0n1-disk/nvme01/ai-document-presentation-v2/player/jobs")
TARGET_HEIGHT = 480

def get_video_height(video_path: Path) -> int:
    """
    Get the height of a video file using ffprobe.
    Returns -1 if height cannot be determined.
    """
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=height',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            return -1
        
        output = result.stdout.strip()
        if not output:
             return -1
             
        return int(output)
    except Exception:
        return -1

def compress_video_file(input_path: Path) -> bool:
    """
    Compress a video file using ffmpeg and replace the original.
    Copied logic from compress_avatar_videos.py but adapted for individual file processing.
    """
    if not input_path.exists():
        return False
    
    # Create temporary output file name in same directory
    temp_output = input_path.parent / f"{input_path.stem}_temp_{os.getpid()}{input_path.suffix}"
    
    # ffmpeg command for compression
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vf', f'scale=-2:{TARGET_HEIGHT}',
        '-c:v', 'libx264',
        '-crf', '28',
        '-preset', 'veryfast',
        '-c:a', 'aac',
        '-b:a', '48k',
        '-y',  # Overwrite output file if it exists
        str(temp_output)
    ]
    
    print(f"  🔄 Compressing...")
    
    try:
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ❌ Error compressing: {result.stderr}")
            if temp_output.exists():
                temp_output.unlink()
            return False
        
        # Get file sizes for comparison
        original_size = input_path.stat().st_size
        compressed_size = temp_output.stat().st_size
        
        if compressed_size >= original_size:
             print(f"  ⚠️ Warning: Compressed size ({compressed_size}) is larger than or equal to original ({original_size}). Keeping original.")
             temp_output.unlink()
             return False

        reduction = ((original_size - compressed_size) / original_size) * 100
        
        # Replace original file with compressed version
        shutil.move(str(temp_output), str(input_path))
        
        print(f"  ✅ Compressed: {original_size / (1024*1024):.2f} MB -> {compressed_size / (1024*1024):.2f} MB ({reduction:.1f}% reduction)")
        return True
        
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        if temp_output.exists():
            temp_output.unlink()
        return False

def process_job(job_dir: Path):
    """
    Process all avatar videos in a single job directory.
    """
    avatars_dir = job_dir / 'avatars'
    if not avatars_dir.exists():
        return

    # Find all .mp4 files
    video_files = list(avatars_dir.glob('*.mp4'))
    if not video_files:
        return

    print(f"📂 Processing Job: {job_dir.name}")
    
    for video in video_files:
        try:
            height = get_video_height(video)
            
            if height == -1:
                print(f"  ❓ Could not determine height for {video.name}, skipping.")
                continue
                
            if height > TARGET_HEIGHT:
                print(f"  📹 Found {video.name} (Height: {height}p > {TARGET_HEIGHT}p)")
                compress_video_file(video)
            else:
                # Optional: Verbose logging
                # print(f"  ⏭️  Skipping {video.name} (Height: {height}p <= {TARGET_HEIGHT}p)")
                pass
                
        except Exception as e:
            print(f"  ❌ Error processing {video.name}: {e}")

def main():
    print(f"🚀 Starting Avatar Compression Automation")
    print(f"📂 Scanning jobs in: {JOBS_DIR}")
    print(f"🎯 Target Height: {TARGET_HEIGHT}p")
    print("=" * 50)
    
    if not JOBS_DIR.exists():
        print(f"❌ Error: Jobs directory not found: {JOBS_DIR}")
        sys.exit(1)
        
    # Iterate through all job directories
    job_dirs = [d for d in JOBS_DIR.iterdir() if d.is_dir()]
    
    for job_dir in sorted(job_dirs):
        process_job(job_dir)
        
    print("=" * 50)
    print("✅ Done processing all jobs.")

if __name__ == "__main__":
    main()
