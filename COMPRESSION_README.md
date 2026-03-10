# Avatar Compression Automation

This script automates the compression of avatar videos across all job directories.

## Overview

The script `process_all_avatars.py` allows you to:
1.  **Scan** all job directories in `/nvme0n1-disk/nvme01/ai-document-presentation-v2/player/jobs`.
2.  **Detect** avatar videos in the `avatars` subdirectory of each job.
3.  **Check** the resolution of each video.
4.  **Compress** videos that are **higher than 480p** (e.g., 720p, 1080p) down to 480p.
5.  **Skip** videos that are already 480p or lower.

## usage

To fun the script, execute the following command in your terminal:

```bash
sudo python3 /nvme0n1-disk/nvme01/ai-document-presentation-v2/process_all_avatars.py
```

## How it works

-   **Input:** Scans `*.mp4` files in `.../player/jobs/*/avatars/`.
-   **Condition:** If `height > 480`, compression is triggered.
-   **Compression Settings:**
    -   Codec: libx264
    -   CRF: 28 (Good balance of quality and size)
    -   Preset: veryfast
    -   Audio: AAC, 48k
-   **Safety:**
    -   It compresses to a temporary file first.
    -   It verifies compression was successful.
    -   It checks if the compressed file is actually smaller (or keeps original if not).
    -   It replaces the original file only after success.

## Logs

The script prints progress to the console, showing which jobs are being processed and which videos are being compressed.
