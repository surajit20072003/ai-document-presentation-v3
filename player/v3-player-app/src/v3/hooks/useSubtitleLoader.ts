import { useState, useEffect } from 'react';
import type { SubtitleData } from '../types';

/**
 * Fetches subtitles.json for a job once on mount.
 * Returns SubtitleData if the file exists, null if not found or on error.
 * The karaoke engine gracefully falls back to character-estimate when null.
 */
export const useSubtitleLoader = (jobId: string): SubtitleData | null => {
    const [data, setData] = useState<SubtitleData | null>(null);

    useEffect(() => {
        if (!jobId) return;
        const url = `/player/jobs/${jobId}/subtitles.json`;
        fetch(url)
            .then((r) => {
                if (!r.ok) return null; // file doesn't exist yet — no error
                return r.json();
            })
            .then((json) => {
                if (json?.version && json?.sections) {
                    setData(json as SubtitleData);
                    console.log(`[subtitles] Loaded exact word timestamps for job ${jobId}`);
                }
            })
            .catch(() => {
                // Network or parse errors — silently fall back to estimation
            });
    }, [jobId]);

    return data;
};
