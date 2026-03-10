#!/usr/bin/env python3
"""
Script to compress avatar videos in place using ffmpeg.
Compresses videos to 480p with optimized settings and replaces the original files.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def compress_video(input_path: str) -> bool:
    """
    Compress a video file using ffmpeg and replace the original.
    
    Args:
        input_path: Path to the input video file
        
    Returns:
        True if compression was successful, False otherwise
    """
    input_file = Path(input_path)
    
    if not input_file.exists():
        print(f"❌ Error: File not found: {input_path}")
        return False
    
    # Create temporary output file name in same directory
    temp_output = input_file.parent / f"{input_file.stem}_temp_{os.getpid()}{input_file.suffix}"
    
    # ffmpeg command for compression
    # -vf scale=-2:480: Scale to 480p height, width auto-calculated to maintain aspect ratio
    # -c:v libx264: Use H.264 codec
    # -crf 28: Constant Rate Factor (quality), higher = more compression
    # -preset veryfast: Encoding speed preset
    # -c:a aac: Use AAC audio codec
    # -b:a 48k: Audio bitrate 48kbps
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', str(input_file),
        '-vf', 'scale=-2:480',
        '-c:v', 'libx264',
        '-crf', '28',
        '-preset', 'veryfast',
        '-c:a', 'aac',
        '-b:a', '48k',
        '-y',  # Overwrite output file if it exists
        str(temp_output)
    ]
    
    print(f"🔄 Compressing: {input_file.name}")
    
    try:
        # Run ffmpeg command
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Error compressing {input_file.name}:")
            print(result.stderr)
            return False
        
        # Get file sizes for comparison
        original_size = input_file.stat().st_size
        compressed_size = temp_output.stat().st_size
        reduction = ((original_size - compressed_size) / original_size) * 100
        
        # Replace original file with compressed version
        shutil.move(str(temp_output), str(input_file))
        
        print(f"✅ Compressed: {input_file.name}")
        print(f"   Original: {original_size / (1024*1024):.2f} MB")
        print(f"   Compressed: {compressed_size / (1024*1024):.2f} MB")
        print(f"   Reduction: {reduction:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Exception while compressing {input_file.name}: {e}")
        # Clean up temp file if it exists
        if temp_output.exists():
            temp_output.unlink()
        return False


def find_avatar_videos(job_path: str) -> list:
    """
    Find all avatar videos in the job directory.
    
    Args:
        job_path: Path to the job directory
        
    Returns:
        List of paths to avatar video files
    """
    job_dir = Path(job_path)
    avatars_dir = job_dir / 'avatars'
    
    if not avatars_dir.exists():
        print(f"❌ Error: Avatars directory not found: {avatars_dir}")
        return []
    
    # Find all .mp4 files in avatars directory
    video_files = list(avatars_dir.glob('*.mp4'))
    
    return [str(f) for f in video_files]


def main():
    """Main function to compress all avatar videos in a job directory."""
    
    if len(sys.argv) < 2:
        print("Usage: python compress_avatar_videos.py <job_directory_path>")
        print("Example: python compress_avatar_videos.py /nvme0n1-disk/nvme01/ai-document-presentation-v2/player/jobs/0cdc982b")
        sys.exit(1)
    
    job_path = sys.argv[1]
    
    print(f"🔍 Searching for avatar videos in: {job_path}")
    
    # Find all avatar videos
    video_files = find_avatar_videos(job_path)
    
    if not video_files:
        print("❌ No avatar videos found.")
        sys.exit(1)
    
    print(f"📹 Found {len(video_files)} avatar video(s)")
    print()
    
    # Compress each video
    success_count = 0
    fail_count = 0
    
    for video_file in video_files:
        if compress_video(video_file):
            success_count += 1
        else:
            fail_count += 1
        print()  # Empty line between videos
    
    # Summary
    print("=" * 50)
    print(f"✅ Successfully compressed: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📊 Total: {len(video_files)}")
    
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
