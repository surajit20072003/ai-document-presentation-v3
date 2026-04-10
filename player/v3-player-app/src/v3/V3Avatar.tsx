import { useRef, useEffect, useCallback, forwardRef, useImperativeHandle, useState } from 'react';
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
        const audioRef = useRef<HTMLAudioElement>(null);
        const canvasRef = useRef<HTMLCanvasElement>(null);
        const prevCanvasRef = useRef<HTMLCanvasElement>(null);
        const overlayRef = useRef<HTMLDivElement>(null);
        // Tracks whether the current section is audio-only (no avatar video).
        // Using a ref (not state) so the getter in useImperativeHandle always reads the latest value.
        const isAudioModeRef = useRef(false);
        const [showCanvas, setShowCanvas] = useState(true);

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
                const avatarPath = getAvatarUrl(section);
                const audioPath = section.audio_path;

                if (!avatarPath && audioPath) {
                    // ── Audio-Only Mode ──
                    // No avatar video — use the <audio> element as the media clock.
                    // All downstream code (timeupdate, ended, karaoke, WAN sync) works unchanged
                    // since <audio> and <video> share the same HTMLMediaElement API.
                    isAudioModeRef.current = true;
                    setShowCanvas(false);

                    const src = getMediaSrc(audioPath, jid);
                    const finalSrc = getBlob?.(src) || src;
                    const aud = audioRef.current;
                    if (!aud) return;
                    aud.src = finalSrc;
                    aud.playbackRate = rate;
                    aud.load();
                    aud.play().catch((err) => console.warn('[V3Avatar] audio play() failed:', err?.message || err));
                    return;
                }

                // ── Normal Avatar-Video Mode ──
                isAudioModeRef.current = false;
                setShowCanvas(true);

                const vid = videoRef.current;
                const canvasCur = canvasRef.current;
                const canvasPrev = prevCanvasRef.current;
                if (!vid || !avatarPath) return;

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
            get video() {
                // Return audio element (typed as HTMLVideoElement) in audio-only mode.
                // They share the same HTMLMediaElement API: currentTime, duration, play(),
                // pause(), src, load(), playbackRate, timeupdate, ended, readyState, paused.
                if (isAudioModeRef.current && audioRef.current) {
                    return audioRef.current as unknown as HTMLVideoElement;
                }
                return videoRef.current;
            },
            loadAvatar,
        }), [loadAvatar]);

        return (
            <div
                ref={overlayRef}
                className="v3-av-overlay"
                data-sectype={sectionType}
                style={{ display: visible ? 'block' : 'none' }}
            >
                {/* Hidden video element — used for avatar mp4 and quiz clips */}
                <video
                    ref={videoRef}
                    playsInline
                    crossOrigin="anonymous"
                    style={{ position: 'absolute', width: '1px', height: '1px', opacity: 0.01, pointerEvents: 'none' }}
                />
                {/* Hidden audio element — used as the media clock in audio-only mode */}
                <audio
                    ref={audioRef}
                    style={{ display: 'none' }}
                />
                {/* Canvas layers — only rendered when an avatar video is present */}
                {showCanvas && (
                    <>
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
                    </>
                )}
            </div>
        );
    }
);
V3Avatar.displayName = 'V3Avatar';
