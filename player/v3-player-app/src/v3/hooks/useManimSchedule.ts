import { useState, useEffect, useRef } from 'react';
import { getMediaSrc } from '../utils';
import type { V3Section } from '../types';

export interface ManimBeat {
    start: number;
    end: number;
    type: 'video' | 'image';
    src: string;
}

interface UseManimScheduleOpts {
    section: V3Section | null;
    jobId: string;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
    manimVideoRef: React.RefObject<HTMLVideoElement | null>;
    getBlob?: (src: string) => string | null;
}

export function useManimSchedule({ section, jobId, avatarVideoRef, manimVideoRef, getBlob }: UseManimScheduleOpts) {
    const [schedule, setSchedule] = useState<ManimBeat[]>([]);
    const [currentBeatIndex, setCurrentBeatIndex] = useState(-1);
    const intervalRef = useRef<number | null>(null);
    const lastBeatRef = useRef(-1);

    useEffect(() => {
        setCurrentBeatIndex(-1);
        lastBeatRef.current = -1;
        if (!section) { setSchedule([]); return; }

        const beats: ManimBeat[] = [];
        const manimPaths = section.manim_video_paths || (section.video_path ? [section.video_path] : []);
        const visualBeats = (section.visual_beats || []).slice().sort((a, b) => (a.beat_start_seconds || 0) - (b.beat_start_seconds || 0));

        if (manimPaths.length === 0 && visualBeats.length === 0) {
            setSchedule([]);
            return;
        }

        const rsBeats = section.render_spec?.manim_beats;
        const useRenderSpec = rsBeats && rsBeats.length > 0 && rsBeats.length >= manimPaths.length;

        if (useRenderSpec) {
            // ── Priority 1: render_spec.manim_beats present ──
            let accT = 0;
            rsBeats.forEach((mb, i) => {
                const dur = mb.duration || mb.duration_seconds || 15;
                const path = manimPaths[i];
                if (path) {
                    beats.push({
                        start: accT,
                        end: accT + dur,
                        type: 'video',
                        src: getMediaSrc(path, jobId)
                    });
                }
                accT += dur;
            });

            // Overlay image beats from visual_beats
            visualBeats.forEach(vb => {
                if ((vb.visual_type === 'image' || vb.visual_type === 'infographic') && (vb.image_source || vb.image_path)) {
                    beats.push({
                        start: vb.beat_start_seconds || 0,
                        end: vb.beat_end_seconds || 9999,
                        type: 'image',
                        src: getMediaSrc(vb.image_source || vb.image_path!, jobId)
                    });
                }
            });
            beats.sort((a, b) => a.start - b.start);

        } else {
            // ── Priority 2: Use visual_beats (fallback 1) ──
            let manimIdx = 0;
            visualBeats.forEach(vb => {
                if ((vb.visual_type === 'image' || vb.visual_type === 'infographic') && (vb.image_source || vb.image_path)) {
                    beats.push({
                        start: vb.beat_start_seconds || 0,
                        end: vb.beat_end_seconds || 9999,
                        type: 'image',
                        src: getMediaSrc(vb.image_source || vb.image_path!, jobId)
                    });
                } else {
                    const path = vb.video_path || manimPaths[manimIdx] || null;
                    manimIdx++;
                    if (path) {
                        beats.push({
                            start: vb.beat_start_seconds || 0,
                            end: vb.beat_end_seconds || 9999,
                            type: 'video',
                            src: getMediaSrc(path, jobId)
                        });
                    }
                }
            });

            // ── Priority 3: No visual_beats, just paths + segments (fallback 2) ──
            if (beats.length === 0 && manimPaths.length > 0) {
                const segs = section.narration?.segments || [];
                let accT2 = 0;
                for (let fi = 0; fi < manimPaths.length; fi++) {
                    const dur2 = segs[fi] ? (segs[fi].duration_seconds || 15) : 15;
                    beats.push({ start: accT2, end: accT2 + dur2, type: 'video', src: getMediaSrc(manimPaths[fi], jobId) });
                    accT2 += dur2;
                }
            }
        }

        // ── infographic_beats override (for completeness, matches player_v3.html logic) ──
        const infos = section.render_spec?.infographic_beats;
        if (infos && infos.length > 0) {
            infos.forEach((ib) => {
                const imgSrc = ib.image_source || ib.image_path;
                if (!imgSrc) return;

                const ibStart = ib.start_seconds || 0;
                const ibEnd = ib.end_seconds || 9999;
                const alreadyExists = beats.some(s => s.type === 'image' && s.src.includes(imgSrc) && Math.abs(s.start - ibStart) < 0.5);

                if (!alreadyExists) {
                    beats.push({
                        start: ibStart,
                        end: ibEnd,
                        type: 'image',
                        src: getMediaSrc(imgSrc, jobId),
                    });
                }
            });
            beats.sort((a, b) => a.start - b.start);
        }

        setSchedule(beats);
    }, [section, jobId]);

    useEffect(() => {
        if (schedule.length === 0) return;
        const sync = () => {
            const avatar = avatarVideoRef.current;
            const manim = manimVideoRef.current;
            if (!avatar || !manim) return;
            const t = avatar.currentTime;

            let idx = -1;
            // Forward scan — last beat has no end guard
            for (let i = 0; i < schedule.length; i++) {
                const isLast = i === schedule.length - 1;
                const hit = isLast
                    ? t >= schedule[i].start
                    : t >= schedule[i].start && t < schedule[i].end;
                if (hit) idx = i;
            }

            if (idx !== lastBeatRef.current) {
                lastBeatRef.current = idx;
                setCurrentBeatIndex(idx);
                if (idx >= 0 && schedule[idx].type === 'video') {
                    const blobSrc = getBlob?.(schedule[idx].src);
                    const finalSrc = blobSrc || schedule[idx].src;
                    if (manim.src !== finalSrc) {
                        manim.src = finalSrc;
                        manim.currentTime = Math.max(0, t - schedule[idx].start);
                    }
                    if (!avatar.paused) manim.play().catch(() => { });
                }
            }

            // Sync video with avatar
            if (idx >= 0 && schedule[idx].type === 'video' && !avatar.paused) {
                const expectedTime = Math.max(0, t - schedule[idx].start);
                // Allow a larger drift threshold for manim videos because they often switch quickly
                if (Math.abs(manim.currentTime - expectedTime) > 0.4) manim.currentTime = expectedTime;

                // Stall recovery
                if (manim.paused && !manim.ended && manim.readyState >= 3 && manim.src) manim.play().catch(() => { });
            }

            if (avatar.paused && !manim.paused) manim.pause();
        };

        intervalRef.current = window.setInterval(sync, 120);
        return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
    }, [schedule, avatarVideoRef, manimVideoRef, getBlob]);

    return { schedule, currentBeatIndex };
}
