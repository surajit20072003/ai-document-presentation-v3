import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { useChromaKey } from './hooks/useChromaKey';
import { getMediaSrc, getAvatarUrl } from './utils';
import type { V3Section } from './types';

export interface V3AvatarHandle {
    video: HTMLVideoElement | null;
    loadAvatar: (section: V3Section, jobId: string, rate: number, getBlob?: (src: string) => string | null) => void;
}

interface V3AvatarProps {
    jobId: string;
    sectionType: string;
    visible: boolean;
}

export const V3Avatar = forwardRef<V3AvatarHandle, V3AvatarProps>(
    ({ jobId: _jobId, sectionType, visible }, ref) => {
        const videoRef = useRef<HTMLVideoElement>(null);
        const canvasRef = useRef<HTMLCanvasElement>(null);
        const prevCanvasRef = useRef<HTMLCanvasElement>(null);
        const overlayRef = useRef<HTMLDivElement>(null);

        const { resizeCanvas, resample } = useChromaKey({
            videoRef,
            canvasRef,
            overlayRef,
            enabled: true,
        });

        useEffect(() => {
            const vid = videoRef.current;
            if (!vid) return;
            const onLoaded = () => { resizeCanvas(); resample(); };
            vid.addEventListener('loadeddata', onLoaded);
            return () => vid.removeEventListener('loadeddata', onLoaded);
        }, [resizeCanvas, resample]);

        const loadAvatar = useCallback(
            (section: V3Section, jid: string, rate: number, getBlob?: (src: string) => string | null) => {
                const vid = videoRef.current;
                const canvasCur = canvasRef.current;
                const canvasPrev = prevCanvasRef.current;
                if (!vid) return;

                const avatarPath = getAvatarUrl(section);
                if (!avatarPath) return;

                // Crossfade: stamp current frame onto prev canvas
                if (canvasCur && canvasPrev && canvasCur.width > 0 && canvasCur.height > 0) {
                    canvasPrev.width = canvasCur.width;
                    canvasPrev.height = canvasCur.height;
                    try {
                        const ctx = canvasPrev.getContext('2d');
                        if (ctx) ctx.drawImage(canvasCur, 0, 0);
                    } catch (_) { }
                    canvasPrev.style.transition = 'opacity 0s';
                    canvasPrev.style.opacity = '1';
                }

                const mediaSrc = getMediaSrc(avatarPath, jid);
                const blobSrc = getBlob?.(mediaSrc);
                const finalSrc = blobSrc || mediaSrc;
                vid.src = finalSrc;
                vid.load();
                vid.playbackRate = rate;
                vid.play().catch((err) => console.warn('[V3Avatar] play() failed:', err?.message || err));

                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        if (canvasPrev) {
                            canvasPrev.style.transition = 'opacity 0.45s ease';
                            canvasPrev.style.opacity = '0';
                        }
                    });
                });
            },
            []
        );

        useImperativeHandle(ref, () => ({
            get video() { return videoRef.current; },
            loadAvatar,
        }), [loadAvatar]);

        return (
            <div
                ref={overlayRef}
                className="v3-av-overlay"
                data-sectype={sectionType}
                style={{ display: visible ? 'block' : 'none' }}
            >
                <video
                    ref={videoRef}
                    playsInline
                    crossOrigin="anonymous"
                    style={{ position: 'absolute', width: '1px', height: '1px', opacity: 0.01, pointerEvents: 'none' }}
                />
                <canvas
                    ref={prevCanvasRef}
                    style={{
                        width: '100%', height: '100%', display: 'block',
                        position: 'absolute', top: 0, left: 0,
                        opacity: 0, transition: 'opacity 0.45s ease',
                        pointerEvents: 'none', zIndex: 2, background: 'transparent',
                    }}
                />
                <canvas
                    ref={canvasRef}
                    style={{
                        width: '100%', height: '100%', display: 'block',
                        position: 'absolute', top: 0, left: 0, zIndex: 1, background: 'transparent',
                    }}
                />
            </div>
        );
    }
);
V3Avatar.displayName = 'V3Avatar';
