import { useRef, useState, useEffect } from 'react';
import { useVideoSchedule } from './hooks/useVideoSchedule';
import { useManimSchedule } from './hooks/useManimSchedule';
import { getSectionType, getMediaSrc } from './utils';
import type { V3Section } from './types';

interface V3ContentLayersProps {
    section: V3Section | null;
    jobId: string;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
    getBlob?: (src: string) => string | null;
}

const MANIM_RENDERERS = ['manim'];
const VIDEO_RENDERERS = ['video', 'wan_video', 'text_to_video', 'image_to_video'];

function getRendererKind(section: V3Section): 'manim' | 'video' | 'image' | 'none' {
    const st = getSectionType(section);
    if (st === 'quiz') return 'none';
    const r = section.renderer?.toLowerCase() || '';
    if (MANIM_RENDERERS.includes(r)) return 'manim';
    if (VIDEO_RENDERERS.includes(r)) return 'video';
    if (st === 'memory_infographic' || st === 'recap') return 'image';
    if (section.manim_video_paths && section.manim_video_paths.length > 0) return 'manim';
    if (section.beat_video_paths && section.beat_video_paths.length > 0) return 'video';
    if (section.visual_beats && section.visual_beats.length > 0) return 'video';
    if (section.video_path) return 'video';
    return 'none';
}

export const V3ContentLayers = ({ section, jobId, avatarVideoRef, getBlob }: V3ContentLayersProps) => {
    const manimVideoRef = useRef<HTMLVideoElement>(null);
    const wanVideoRef = useRef<HTMLVideoElement>(null);
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [imageVisible, setImageVisible] = useState(false);

    const kind = section ? getRendererKind(section) : 'none';

    useEffect(() => {
        const wan = wanVideoRef.current;
        const manim = manimVideoRef.current;
        if (wan) { wan.pause(); wan.removeAttribute('src'); wan.load(); }
        if (manim) { manim.pause(); manim.removeAttribute('src'); manim.load(); }
        setImageVisible(false);
        setImageUrl(null);
    }, [section]);

    const { schedule: videoSchedule, currentBeatIndex: videoBeatIdx } = useVideoSchedule({
        // Bug 1 fix: also enable for 'image' kind (memory_infographic) to load infographic_beats
        section: (kind === 'video' || kind === 'image') ? section : null,
        jobId, avatarVideoRef, getBlob,
    });

    const { schedule: manimSchedule, currentBeatIndex: manimBeatIdx } = useManimSchedule({
        section: kind === 'manim' ? section : null,
        jobId, avatarVideoRef, manimVideoRef, getBlob,
    });

    // ── FIX: Switch video src AND always play — mirrors player_v3.html showBeat() ──
    useEffect(() => {
        const vid = wanVideoRef.current;
        if (!vid || kind !== 'video') return;
        if (videoBeatIdx >= 0 && videoSchedule[videoBeatIdx]) {
            const beat = videoSchedule[videoBeatIdx];
            if (beat.type === 'video') {
                const src = beat.blobUrl || beat.src;
                if (vid.src !== src) {
                    vid.src = src;
                    vid.currentTime = 0;
                    vid.load();
                }
                // Always try to play — even if src matches, video may have ended/stalled
                if (vid.paused || vid.ended) vid.play().catch(() => { });
            }
        }
    }, [videoBeatIdx, videoSchedule, kind]);

    // ── Image layer logic ──
    useEffect(() => {
        if ((kind === 'video' || kind === 'image') && videoBeatIdx >= 0 && videoSchedule[videoBeatIdx]?.type === 'image') {
            const imgSrc = videoSchedule[videoBeatIdx].src;
            const blobSrc = getBlob?.(imgSrc);
            setImageUrl(blobSrc || imgSrc);
            requestAnimationFrame(() => setImageVisible(true));
        } else if (kind === 'manim' && manimBeatIdx >= 0 && manimSchedule[manimBeatIdx]?.type === 'image') {
            const imgSrc = manimSchedule[manimBeatIdx].src;
            const blobSrc = getBlob?.(imgSrc);
            setImageUrl(blobSrc || imgSrc);
            requestAnimationFrame(() => setImageVisible(true));
        } else {
            setImageVisible(false);
            setTimeout(() => setImageUrl(null), 400);
        }
    }, [kind, videoBeatIdx, manimBeatIdx, videoSchedule, manimSchedule, getBlob]);

    // ── Fallback: single video_path with no schedule ──
    useEffect(() => {
        if (kind !== 'video') return;
        if (videoSchedule.length > 0) return;
        const vid = wanVideoRef.current;
        if (!vid || !section?.video_path) return;
        const proxySrc = getMediaSrc(section.video_path, jobId);
        const blobSrc = getBlob?.(proxySrc);
        const finalSrc = blobSrc || proxySrc;
        vid.src = finalSrc;
        vid.currentTime = 0;
        vid.play().catch(() => { });
    }, [section, jobId, kind, videoSchedule.length, getBlob]);

    // ── Bug 3 Fix: Pause WAN when avatar pauses, resume when it resumes ──
    // Also handles stall recovery (mirrors player_v3.html line 2827-2830)
    useEffect(() => {
        if (kind !== 'video' && kind !== 'image') return;
        const iv = window.setInterval(() => {
            const avatar = avatarVideoRef.current;
            const wan = wanVideoRef.current;
            if (!avatar || !wan) return;
            // Actively pause WAN when avatar pauses
            if (avatar.paused) {
                if (!wan.paused) wan.pause();
                return;
            }
            // Stall recovery: restart stalled WAN while avatar is playing
            if (wan.paused && !wan.ended && wan.readyState >= 3 && wan.src) {
                wan.play().catch(() => { });
            }
        }, 250);
        return () => clearInterval(iv);
    }, [kind, avatarVideoRef]);


    const showWan = kind === 'video';
    const showManim = kind === 'manim';
    const showImage = !!imageUrl;

    return (
        <>
            <div className={`v3-wan-layer ${showWan ? 'on' : ''}`}>
                <video ref={wanVideoRef} className="v3-layer-video" playsInline muted crossOrigin="anonymous" />
            </div>
            <div className={`v3-manim-layer ${showManim ? 'on' : ''}`}>
                <video ref={manimVideoRef} className="v3-layer-video" playsInline muted crossOrigin="anonymous" />
            </div>
            <div className={`v3-image-layer ${showImage ? 'on' : ''} ${imageVisible ? 'vis' : ''}`}>
                {imageUrl && (
                    <img
                        className="v3-layer-image"
                        src={imageUrl}
                        alt=""
                        onError={(e) => {
                            const img = e.currentTarget;
                            const src = img.src;
                            if (src.endsWith('.png')) img.src = src.replace('.png', '.jpg');
                            else if (src.endsWith('.jpg')) img.src = src.replace('.jpg', '.jpeg');
                        }}
                    />
                )}
            </div>
        </>
    );
};
