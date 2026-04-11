import { useState, useEffect, useCallback, useRef } from 'react';
import { V3TopBar } from './V3TopBar';
import { V3BottomBar } from './V3BottomBar';
import { V3Avatar, type V3AvatarHandle } from './V3Avatar';
import { V3ContentLayers } from './V3ContentLayers';
import { V3Subtitles } from './V3Subtitles';
import { V3IntroScene } from './sections/V3IntroScene';
import { V3SummaryScene } from './sections/V3SummaryScene';
import { V3MemoryScene } from './sections/V3MemoryScene';
import { V3RecapScene } from './sections/V3RecapScene';
import { V3QuizScene } from './sections/V3QuizScene';
import { useMediaPreloader } from './hooks/useMediaPreloader';
import { useSubtitleLoader } from './hooks/useSubtitleLoader';
import { V3ExplanationVisualLayer } from './V3ExplanationVisualLayer';
import { getSectionType } from './utils';
import type { V3Presentation, V3Section, SubtitleMode, V3ExplanationVisual } from './types';
import './v3-player.css';

interface V3PlayerProps {
    jobId: string;
    onClose: () => void;
}

export const V3Player = ({ jobId, onClose }: V3PlayerProps) => {
    const [presentation, setPresentation] = useState<V3Presentation | null>(null);
    const [sections, setSections] = useState<V3Section[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [playbackRate, setPlaybackRate] = useState(1);
    const [progress, setProgress] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [subtitleMode, setSubtitleMode] = useState<SubtitleMode>('karaoke');
    const [showTapToStart, setShowTapToStart] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [totalTime, setTotalTime] = useState(0);
    const [showQuiz, setShowQuiz] = useState(false);
    const [explanationVisual, setExplanationVisual] = useState<V3ExplanationVisual | null>(null);
    const [quizSubtitleText, setQuizSubtitleText] = useState<string | null>(null);
    const avatarRef = useRef<V3AvatarHandle>(null);
    const needsAutoStart = useRef(false);

    const [isFullscreen, setIsFullscreen] = useState(false);
    const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
    const [isPortrait, setIsPortrait] = useState(
        () => typeof window !== 'undefined' ? window.matchMedia('(orientation: portrait)').matches : false
    );

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const { getBlob, initialReady, cacheProgress } = useMediaPreloader(sections, currentIndex, jobId);
    // Load subtitles.json (word-level timestamps from subtitle_aligner.py).
    // Returns null if file not yet generated → falls back to character-estimate.
    const subtitleData = useSubtitleLoader(jobId);

    useEffect(() => {
        const url = `/player/jobs/${jobId}/presentation.json?t=${Date.now()}`;
        fetch(url)
            .then((r) => {
                if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
                return r.json();
            })
            .then((data: V3Presentation) => {
                if (!data.sections || data.sections.length === 0) throw new Error('presentation.json has no sections');
                setPresentation(data);
                setSections(data.sections);
                setLoading(false);

                const isMobileDevice = /Android|iPhone|iPad/i.test(navigator.userAgent);
                if (isMobileDevice) {
                    setShowTapToStart(true);
                } else {
                    needsAutoStart.current = true;
                }
            })
            .catch((err) => {
                setError(err.message || 'Failed to load presentation');
                setLoading(false);
            });
    }, [jobId]);

    const loadSection = useCallback((index: number, secs?: V3Section[]) => {
        const s = secs || sections;
        if (index < 0 || index >= s.length) return;

        setCurrentIndex(index);
        setProgress(0);
        setIsPlaying(true);
        setShowQuiz(false);
        setExplanationVisual(null);
        setQuizSubtitleText(null);

        if (avatarRef.current) {
            avatarRef.current.loadAvatar(s[index], jobId, playbackRate, getBlob);
        }
    }, [sections, jobId, playbackRate, getBlob]);

    useEffect(() => {
        if (!loading && sections.length > 0 && needsAutoStart.current && initialReady) {
            needsAutoStart.current = false;
            loadSection(0);
        }
    }, [loading, sections, loadSection, initialReady]);

    useEffect(() => {
        const vid = avatarRef.current?.video;
        if (!vid) return;

        const onTimeUpdate = () => {
            if (vid.duration && isFinite(vid.duration)) {
                setProgress((vid.currentTime / vid.duration) * 100);
                setCurrentTime(vid.currentTime);
                setTotalTime(vid.duration);
            }
        };

        const onEnded = () => {
            const sec = sections[currentIndex];
            const secType = getSectionType(sec);
            const hasEmbeddedQuiz = secType !== 'quiz' && ((sec.questions && sec.questions.length > 0) || sec.understanding_quiz);

            if (hasEmbeddedQuiz) {
                setShowQuiz(true);
                return;
            }

            if (secType !== 'quiz' && !showQuiz) setIsPlaying(false);
            if (secType !== 'quiz' && currentIndex < sections.length - 1) loadSection(currentIndex + 1);
        };

        vid.addEventListener('timeupdate', onTimeUpdate);
        vid.addEventListener('ended', onEnded);
        return () => {
            vid.removeEventListener('timeupdate', onTimeUpdate);
            vid.removeEventListener('ended', onEnded);
        };
    }, [currentIndex, sections, loadSection, isPlaying, showQuiz]);

    const handleTogglePlay = useCallback(() => {
        const vid = avatarRef.current?.video;
        if (!vid) return;
        if (isPlaying) { vid.pause(); setIsPlaying(false); }
        else { vid.play().catch(() => { }); setIsPlaying(true); }
    }, [isPlaying]);

    const handleSpeedChange = useCallback((rate: number) => {
        setPlaybackRate(rate);
        const vid = avatarRef.current?.video;
        if (vid) vid.playbackRate = rate;
    }, []);

    const handleReplay = useCallback(() => loadSection(currentIndex), [currentIndex, loadSection]);
    const handlePrev = useCallback(() => { if (currentIndex > 0) loadSection(currentIndex - 1); }, [currentIndex, loadSection]);
    const handleNext = useCallback(() => { if (currentIndex < sections.length - 1) loadSection(currentIndex + 1); }, [currentIndex, sections.length, loadSection]);
    const handleTapToStart = useCallback(() => { setShowTapToStart(false); loadSection(0); }, [loadSection]);

    const handleSeek = useCallback((percent: number) => {
        const vid = avatarRef.current?.video;
        if (!vid || !isFinite(vid.duration)) return;
        vid.currentTime = percent * vid.duration;
    }, []);

    const handleToggleVolume = useCallback(() => {
        const vid = avatarRef.current?.video;
        if (vid) { vid.muted = !vid.muted; setIsMuted(vid.muted); }
    }, []);

    const playerRef = useRef<HTMLDivElement>(null);

    const handleToggleFullscreen = useCallback(async () => {
        if (!playerRef.current) return;
        try {
            if (document.fullscreenElement) {
                await document.exitFullscreen();
                if (isMobile && screen.orientation) try { screen.orientation.unlock(); } catch { }
            } else {
                await playerRef.current.requestFullscreen();
                if (isMobile && screen.orientation) try { await (screen.orientation as any).lock('landscape'); } catch { }
            }
        } catch { }
    }, [isMobile]);

    useEffect(() => {
        const onFSChange = () => setIsFullscreen(!!document.fullscreenElement);
        document.addEventListener('fullscreenchange', onFSChange);
        return () => document.removeEventListener('fullscreenchange', onFSChange);
    }, []);

    useEffect(() => {
        const mql = window.matchMedia('(orientation: portrait)');
        const onChange = (e: MediaQueryListEvent) => setIsPortrait(e.matches);
        mql.addEventListener('change', onChange);
        return () => mql.removeEventListener('change', onChange);
    }, []);

    const title = presentation?.presentation_title || presentation?.title || sections[0]?.title || 'Lesson';
    const currentSection = sections[currentIndex];
    const sectionType = currentSection ? getSectionType(currentSection) : 'content';
    // Stable ref — same object across renders, .current always up-to-date.
    // An inline `{ current: ... }` would create a new object on every render,
    // causing useKaraokeEngine effects to reset on every timeupdate re-render.
    const avatarVideoRef = useRef<HTMLVideoElement | null>(null);
    avatarVideoRef.current = avatarRef.current?.video || null;

    const renderScene = () => {
        if (!currentSection) return null;
        switch (sectionType) {
            case 'intro': return <V3IntroScene section={currentSection} />;
            case 'summary': return <V3SummaryScene section={currentSection} avatarVideoRef={avatarVideoRef} />;
            case 'memory': return <V3MemoryScene section={currentSection} avatarVideoRef={avatarVideoRef} />;
            case 'recap': return <V3RecapScene section={currentSection} avatarVideoRef={avatarVideoRef} />;
            default: return null;
        }
    };

    if (loading || !initialReady) {
        const pct = cacheProgress.total > 0 ? Math.round((cacheProgress.loaded / cacheProgress.total) * 100) : 0;
        return (
            <div className="v3-player">
                <div className="v3-loading-screen">
                    <div className="v3-loading-spinner" />
                    <div className="v3-loading-text">{loading ? 'Loading lesson...' : `Loading your videos... ${pct}%`}</div>
                    {!loading && (
                        <div style={{ width: 200, marginTop: 12, height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, overflow: 'hidden' }}>
                            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--v3-gold)', transition: 'width 0.3s' }} />
                        </div>
                    )}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="v3-player">
                <div className="v3-error-screen">
                    <div style={{ fontSize: 48 }}>⚠️</div>
                    <div style={{ fontSize: 14, color: 'var(--v3-rose)', textAlign: 'center', maxWidth: 400, lineHeight: 1.6 }}>{error}</div>
                    <button className="v3-nb" onClick={onClose} style={{ marginTop: 12, padding: '8px 20px', width: 'auto' }}>Close</button>
                </div>
            </div>
        );
    }

    return (
        <div className={`v3-player${isMobile ? ' v3-player--mobile' : ''}${isMobile && isPortrait ? ' v3-player--portrait' : ''}${isMobile && !isPortrait ? ' v3-player--landscape' : ''}${isFullscreen ? ' v3-player--fullscreen' : ''}`} ref={playerRef}>
            {showTapToStart && (
                <div className="v3-tap-to-start" onClick={handleTapToStart}>
                    <div style={{ fontSize: 48 }}>▶️</div>
                    <div style={{ fontSize: 18, fontWeight: 600 }}>Tap to start lesson</div>
                    <div style={{ fontSize: 13, color: 'rgba(230,237,243,0.5)' }}>Audio required</div>
                </div>
            )}

            <V3TopBar title={title} sections={sections} currentIndex={currentIndex} onSectionClick={(i) => loadSection(i)} onClose={onClose} isMobile={isMobile} />

            <div className={`v3-main ${sectionType === 'intro' ? 'v3-main--fullscreen' : ''}`}>
                {/* V3ContentLayers: hide during quiz UNLESS an explanation visual is showing */}
                <V3ContentLayers
                    section={(sectionType === 'quiz' || showQuiz) && !explanationVisual ? null : currentSection}
                    jobId={jobId}
                    avatarVideoRef={avatarVideoRef}
                    getBlob={getBlob}
                />
                <div className="v3-scene on">{renderScene()}</div>
                {(sectionType === 'quiz' || showQuiz) && currentSection && (
                    <V3QuizScene
                        section={currentSection}
                        jobId={jobId}
                        avatarRef={avatarRef}
                        playbackRate={playbackRate}
                        getBlob={getBlob}
                        onPrevSection={handlePrev}
                        onNextSection={() => {
                            if (showQuiz) { setShowQuiz(false); setExplanationVisual(null); if (currentIndex < sections.length - 1) loadSection(currentIndex + 1); }
                            else handleNext();
                        }}
                        onShowExplanationVisual={(visual) => setExplanationVisual(visual || null)}
                        onHideExplanationVisual={() => setExplanationVisual(null)}
                        onSubtitleText={(text) => setQuizSubtitleText(text)}
                    />
                )}
                {/* Explanation visual overlay — plays AFTER answer, BEFORE next question */}
                <V3ExplanationVisualLayer
                    visual={explanationVisual}
                    jobId={jobId}
                    playbackRate={playbackRate}
                    getBlob={getBlob}
                />
                <V3Avatar ref={avatarRef} jobId={jobId} sectionType={sectionType} visible={sections.length > 0} />
            </div>

            <V3Subtitles
                section={currentSection || null}
                avatarVideoRef={avatarVideoRef}
                mode={subtitleMode}
                overrideText={quizSubtitleText}
                exactWords={subtitleData?.sections[String(currentSection?.section_id)]?.words ?? null}
            />

            <V3BottomBar sections={sections} currentIndex={currentIndex} isPlaying={isPlaying} playbackRate={playbackRate} progress={progress} currentTime={currentTime} totalTime={totalTime} isMuted={isMuted} subtitleMode={subtitleMode} isMobile={isMobile} onPrev={handlePrev} onNext={handleNext} onReplay={handleReplay} onTogglePlay={handleTogglePlay} onSpeedChange={handleSpeedChange} onSeek={handleSeek} onToggleVolume={handleToggleVolume} onToggleFullscreen={handleToggleFullscreen} onSectionClick={(i) => loadSection(i)} onSubtitleToggle={() => setSubtitleMode((m) => m === 'karaoke' ? 'full' : m === 'full' ? 'off' : 'karaoke')} />
        </div>
    );
};
