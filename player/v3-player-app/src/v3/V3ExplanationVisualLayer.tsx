import { useEffect, useRef, useState } from 'react';
import { getMediaSrc } from './utils';
import type { V3ExplanationVisual } from './types';

interface V3ExplanationVisualLayerProps {
    visual: V3ExplanationVisual | null;
    jobId: string;
    playbackRate?: number;
    getBlob?: (src: string) => string | null;
}

/**
 * Renders the explanation_visual for quiz answers — mirrors player_v3.html's showExplanationVisual().
 *
 * Priority for video: visual.video_path → visual.wan_video_path → image_to_video_beats[0].video/wan
 * Fallback for image:  visual.image_source → visual.image_path
 * If neither exists, renders nothing (quiz UI stays visible).
 */
export const V3ExplanationVisualLayer = ({
    visual,
    jobId,
    playbackRate = 1,
    getBlob,
}: V3ExplanationVisualLayerProps) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [imgSrc, setImgSrc] = useState<string | null>(null);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (!visual) {
            setVisible(false);
            setImgSrc(null);
            return;
        }

        // -- 1. Resolve video path (same priority as player_v3.html) --
        let vpath: string | null =
            visual.video_path || visual.wan_video_path || null;

        if (!vpath && visual.image_to_video_beats && visual.image_to_video_beats.length > 0) {
            const eb = visual.image_to_video_beats[0];
            vpath = eb.video_path || eb.wan_video_path || null;
        }

        // -- 2. Resolve image fallback --
        const imageSrc: string | null = visual.image_source || visual.image_path || null;

        // -- 3. If nothing to show, bail out silently (quiz UI stays) --
        if (!vpath && !imageSrc) {
            setVisible(false);
            setImgSrc(null);
            return;
        }

        // -- 4. Play video or show image --
        if (vpath) {
            const proxySrc = getMediaSrc(vpath, jobId);
            const blobSrc = getBlob?.(proxySrc);
            const finalSrc = blobSrc || proxySrc;

            const vid = videoRef.current;
            if (vid) {
                vid.src = finalSrc;
                vid.playbackRate = playbackRate;
                vid.load();
                vid.play().catch(() => { });
            }
            setImgSrc(null);
        } else if (imageSrc) {
            const proxySrc = getMediaSrc(imageSrc, jobId);
            const blobSrc = getBlob?.(proxySrc);
            setImgSrc(blobSrc || proxySrc);
        }

        // Fade in
        requestAnimationFrame(() => {
            requestAnimationFrame(() => setVisible(true));
        });

        return () => {
            const vid = videoRef.current;
            if (vid) { vid.pause(); vid.src = ''; }
            setVisible(false);
            setImgSrc(null);
        };
    }, [visual, jobId, playbackRate, getBlob]);

    // Sync playback rate changes
    useEffect(() => {
        const vid = videoRef.current;
        if (vid && vid.src) vid.playbackRate = playbackRate;
    }, [playbackRate]);

    if (!visual) return null;

    return (
        <div
            className="v3-explanation-visual-layer"
            style={{
                position: 'absolute',
                inset: 0,
                zIndex: 25, // above content layers (wan=10, manim=12, image=15), below avatar (30)
                opacity: visible ? 1 : 0,
                transition: 'opacity 0.3s ease',
                background: 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
            }}
        >
            {/* Video element — always in DOM for quick loading */}
            <video
                ref={videoRef}
                playsInline
                crossOrigin="anonymous"
                style={{
                    position: 'absolute',
                    inset: 0,
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain',
                    background: '#0d1117',
                    display: imgSrc ? 'none' : 'block',
                }}
            />
            {/* Image fallback */}
            {imgSrc && (
                <img
                    src={imgSrc}
                    alt="Explanation visual"
                    style={{
                        position: 'absolute',
                        inset: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain',
                    }}
                    onError={(e) => {
                        const img = e.currentTarget;
                        if (img.src.endsWith('.png')) img.src = img.src.replace('.png', '.jpg');
                        else if (img.src.endsWith('.jpg')) img.src = img.src.replace('.jpg', '.jpeg');
                    }}
                />
            )}
        </div>
    );
};
