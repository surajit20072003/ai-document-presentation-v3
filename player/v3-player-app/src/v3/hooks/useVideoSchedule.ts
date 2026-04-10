import { useState, useEffect, useRef } from 'react';
import { getMediaSrc } from '../utils';
import type { V3Section } from '../types';

export interface BeatEntry {
    start: number;
    end: number;
    type: 'video' | 'image';
    src: string;
    blobUrl?: string;
}

interface UseVideoScheduleOpts {
    section: V3Section | null;
    jobId: string;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
    getBlob?: (src: string) => string | null;
}

export function useVideoSchedule({ section, jobId, avatarVideoRef, getBlob }: UseVideoScheduleOpts) {
    const [schedule, setSchedule] = useState<BeatEntry[]>([]);
    const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
    const blobCacheRef = useRef<Map<string, string>>(new Map());
    const epochRef = useRef(0);

    useEffect(() => {
        epochRef.current++;
        const epoch = epochRef.current;
        blobCacheRef.current.forEach((url) => URL.revokeObjectURL(url));
        blobCacheRef.current.clear();
        setCurrentBeatIndex(-1);

        if (!section) { setSchedule([]); return; }

        const beats: BeatEntry[] = [];

        if (section.visual_beats && section.visual_beats.length > 0) {
            for (const vb of section.visual_beats) {
                const isImageBeat = vb.visual_type === 'image' || vb.visual_type === 'infographic';
                const path = isImageBeat
                    ? (vb.image_source || vb.image_path || vb.video_path || '')
                    : (vb.video_path || vb.image_source || '');
                if (!path) continue;
                beats.push({
                    start: vb.beat_start_seconds,
                    end: vb.beat_end_seconds,
                    type: vb.visual_type === 'image' || vb.visual_type === 'infographic' ? 'image' : 'video',
                    src: getMediaSrc(path, jobId),
                });
            }
        } else if (section.beat_video_paths && section.beat_video_paths.length > 0) {
            const segs = section.narration?.segments || [];
            let cumTime = 0;
            section.beat_video_paths.forEach((p, i) => {
                const dur = segs[i]?.duration_seconds || segs[i]?.duration || 10;
                beats.push({ start: cumTime, end: cumTime + dur, type: 'video', src: getMediaSrc(p, jobId) });
                cumTime += dur;
            });
        }

        const infos = section.render_spec?.infographic_beats;
        if (infos && infos.length > 0) {
            for (const ib of infos) {
                const imgSrc = ib.image_source || ib.image_path;
                if (!imgSrc) continue;
                beats.push({ start: ib.start_seconds || 0, end: ib.end_seconds || 9999, type: 'image', src: getMediaSrc(imgSrc, jobId) });
            }
            beats.sort((a, b) => a.start - b.start);
        }

        const updatedBeats = beats.map((b) => {
            const blob = getBlob?.(b.src);
            return blob ? { ...b, blobUrl: blob } : b;
        });
        setSchedule(updatedBeats);
        // ── FIX: show beat 0 immediately (mirrors player_v3.html showBeat(0)) ──
        // Without this, the first beat is never triggered because the timeupdate
        // listener attaches asynchronously after the schedule useState update.
        if (updatedBeats.length > 0) setCurrentBeatIndex(0);

        updatedBeats.forEach((b) => {
            if (b.type !== 'video' || b.blobUrl) return;
            fetch(b.src)
                .then((r) => r.blob())
                .then((blob) => {
                    if (epochRef.current !== epoch) return;
                    const url = URL.createObjectURL(blob);
                    blobCacheRef.current.set(b.src, url);
                    setSchedule((prev) => prev.map((e) => (e.src === b.src ? { ...e, blobUrl: url } : e)));
                })
                .catch(() => { });
        });

        return () => { };
    }, [section, jobId]);

    useEffect(() => {
        const vid = avatarVideoRef.current;
        if (!vid || schedule.length === 0) return;
        const onTime = () => {
            const t = vid.currentTime;
            let idx = -1;
            // Forward scan — last beat has no end guard (matches player_v3.html line 2815-2818)
            // break after first hit — mirrors HTML player which uses break, ensuring the
            // earliest matching beat wins (prevents isLast open-end guard from hijacking t=0)
            for (let i = 0; i < schedule.length; i++) {
                const isLast = i === schedule.length - 1;
                const hit = isLast
                    ? t >= schedule[i].start
                    : t >= schedule[i].start && t < schedule[i].end;
                if (hit) { idx = i; break; }
            }
            setCurrentBeatIndex(idx);
        };
        vid.addEventListener('timeupdate', onTime);
        return () => vid.removeEventListener('timeupdate', onTime);
    }, [avatarVideoRef, schedule]);

    useEffect(() => {
        return () => { blobCacheRef.current.forEach((url) => URL.revokeObjectURL(url)); };
    }, []);

    return { schedule, currentBeatIndex };
}
