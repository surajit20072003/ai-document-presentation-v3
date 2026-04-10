import { useState, useEffect, useCallback, useRef } from 'react';
import type { V3Section, V3Question } from '../types';
import type { V3AvatarHandle } from '../V3Avatar';
import { getMediaSrc } from '../utils';

interface V3QuizSceneProps {
    section: V3Section;
    jobId: string;
    avatarRef: React.RefObject<V3AvatarHandle | null>;
    playbackRate: number;
    getBlob?: (src: string) => string | null;
    onPrevSection: () => void;
    onNextSection: () => void;
    onShowExplanationVisual?: (visual: V3Question['explanation_visual']) => void;
    onHideExplanationVisual?: () => void;
    onSubtitleText?: (text: string | null) => void;
}

type QuizPhase = 'question' | 'answered' | 'explanation' | 'explanation_visual';

export const V3QuizScene = ({
    section, jobId, avatarRef, playbackRate, getBlob,
    onPrevSection, onNextSection, onShowExplanationVisual, onHideExplanationVisual, onSubtitleText,
}: V3QuizSceneProps) => {
    const questions: V3Question[] = section.questions?.length
        ? section.questions
        : section.understanding_quiz ? [section.understanding_quiz] : [];

    const [qIndex, setQIndex] = useState(0);
    const qIndexRef = useRef(0);
    const [phase, setPhase] = useState<QuizPhase>('question');
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [revealedOptions, setRevealedOptions] = useState<number>(0);
    const [clickable, setClickable] = useState(false);
    const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    const q = questions[qIndex];

    const isAudioOnly = !!section.audio_path;
    const getClipUrl = useCallback((phase: 'question' | 'correct' | 'wrong' | 'explanation', question: V3Question) => {
        if (isAudioOnly && question.audio_clips?.[phase]) return question.audio_clips[phase];
        return question.avatar_clips?.[phase];
    }, [isAudioOnly]);

    const clearTimers = useCallback(() => { timersRef.current.forEach(clearTimeout); timersRef.current = []; }, []);

    const playClip = useCallback((clipUrl: string | undefined, onDone?: () => void) => {
        if (!clipUrl || !avatarRef.current?.video) { onDone?.(); return; }
        const vid = avatarRef.current.video;
        const proxySrc = getMediaSrc(clipUrl, jobId);
        const blobSrc = getBlob?.(proxySrc);
        const finalSrc = blobSrc || proxySrc;
        const handler = () => { vid.removeEventListener('ended', handler); onDone?.(); };
        vid.src = finalSrc; vid.load(); vid.playbackRate = playbackRate;
        vid.play().catch(() => { });
        if (onDone) vid.addEventListener('ended', handler);
    }, [avatarRef, jobId, playbackRate, getBlob]);

    const advanceQuestion = useCallback(() => {
        onHideExplanationVisual?.();
        onSubtitleText?.(null);
        const currentIdx = qIndexRef.current;
        if (currentIdx < questions.length - 1) showQuestion(currentIdx + 1);
        else onNextSection();
    }, [questions.length, onNextSection, onHideExplanationVisual, onSubtitleText]);

    const showQuestion = useCallback((idx: number) => {
        const question = questions[idx];
        if (!question) return;
        setQIndex(idx); qIndexRef.current = idx;
        setPhase('question'); setSelectedKey(null); setRevealedOptions(0); setClickable(false);
        clearTimers();
        const narr = question.narration;
        const optionKeys = Object.keys(question.options || {});
        const revealDelays = narr?.option_reveal_seconds || question.option_reveal_seconds;
        if (revealDelays && revealDelays.length > 0) {
            revealDelays.forEach((delay, i) => {
                if (i < optionKeys.length) {
                    const t = setTimeout(() => setRevealedOptions(prev => Math.max(prev, i + 1)), (delay * 1000) / playbackRate);
                    timersRef.current.push(t);
                }
            });
        } else {
            optionKeys.forEach((_, i) => {
                const t = setTimeout(() => setRevealedOptions(prev => Math.max(prev, i + 1)), (500 + i * 400) / playbackRate);
                timersRef.current.push(t);
            });
        }
        playClip(getClipUrl('question', question), () => { setRevealedOptions(optionKeys.length); setClickable(true); });
        onSubtitleText?.(question.narration?.question_script || null);
        if (!getClipUrl('question', question)) {
            const t = setTimeout(() => { setRevealedOptions(optionKeys.length); setClickable(true); }, (500 + optionKeys.length * 400) / playbackRate);
            timersRef.current.push(t);
        }
    }, [questions, playClip, clearTimers, playbackRate, getClipUrl]);

    useEffect(() => { if (questions.length > 0) showQuestion(0); return clearTimers; }, [section.section_id]);

    const handleAnswer = useCallback((key: string) => {
        if (phase !== 'question' || !clickable || !q) return;
        setSelectedKey(key); setPhase('answered'); setClickable(false);
        const correctKey = q.correct_option || q.correct;
        const isCorrect = key === correctKey;
        const clipUrl = getClipUrl(isCorrect ? 'correct' : 'wrong', q);
        const feedbackScript = isCorrect ? q.narration?.correct_script : q.narration?.wrong_script;
        onSubtitleText?.(feedbackScript || null);
        playClip(clipUrl, () => {
            const expVisual = q.explanation_visual;
            const hasExpVisual = expVisual && (expVisual.video_path || expVisual.wan_video_path || expVisual.image_path || expVisual.image_source);
            const expClip = getClipUrl('explanation', q);
            if (hasExpVisual) {
                setPhase('explanation_visual'); onShowExplanationVisual?.(expVisual);
                onSubtitleText?.(q.narration?.explanation_script || null);
                playClip(expClip, () => { const t = setTimeout(() => advanceQuestion(), 900 / playbackRate); timersRef.current.push(t); });
                if (!expClip) { const t = setTimeout(() => advanceQuestion(), 3000 / playbackRate); timersRef.current.push(t); }
            } else if (q.explanation) {
                setPhase('explanation');
                onSubtitleText?.(q.narration?.explanation_script || null);
                playClip(expClip, () => { const t = setTimeout(() => advanceQuestion(), 900 / playbackRate); timersRef.current.push(t); });
                if (!expClip) { const t = setTimeout(() => advanceQuestion(), 3000 / playbackRate); timersRef.current.push(t); }
            } else {
                const t = setTimeout(() => advanceQuestion(), 900 / playbackRate);
                timersRef.current.push(t);
            }
        });
        if (!clipUrl) {
            const expVisual2 = q.explanation_visual;
            const hasExpVisual2 = expVisual2 && (expVisual2.video_path || expVisual2.wan_video_path || expVisual2.image_path || expVisual2.image_source);
            if (hasExpVisual2) {
                setPhase('explanation_visual'); onShowExplanationVisual?.(expVisual2);
                onSubtitleText?.(q.narration?.explanation_script || null);
                const expClip2 = getClipUrl('explanation', q);
                playClip(expClip2, () => { const t = setTimeout(() => advanceQuestion(), 900 / playbackRate); timersRef.current.push(t); });
                if (!expClip2) { const t = setTimeout(() => advanceQuestion(), 3000 / playbackRate); timersRef.current.push(t); }
            } else if (q.explanation) {
                setPhase('explanation'); onSubtitleText?.(q.narration?.explanation_script || null); const t = setTimeout(() => advanceQuestion(), 3000 / playbackRate); timersRef.current.push(t);
            } else { const t = setTimeout(() => advanceQuestion(), 900 / playbackRate); timersRef.current.push(t); }
        }
    }, [phase, clickable, q, playClip, getClipUrl, advanceQuestion, onShowExplanationVisual, playbackRate, onSubtitleText]);

    if (!q || questions.length === 0 || phase === 'explanation_visual') return null;

    const correctKey = q.correct_option || q.correct;
    const questionText = q.question_text || q.question;
    const optionEntries = Object.entries(q.options || {});
    const showResult = phase !== 'question';

    return (
        <div className="v3-quiz-overlay">
            <div className="v3-quiz-body" style={{ maxWidth: 560, width: '100%' }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: '0.14em', color: 'var(--v3-gold)', marginBottom: 10, textTransform: 'uppercase' }}>
                    QUESTION {qIndex + 1} OF {questions.length}
                </div>
                <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.5, marginBottom: 24, color: 'var(--v3-w)' }}>{questionText}</div>
                <div className="v3-quiz-options-scroll">
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {optionEntries.map(([key, text], i) => {
                            const revealed = i < revealedOptions;
                            const isSelected = selectedKey === key;
                            const isCorrectOpt = key === correctKey;
                            let className = 'v3-quiz-opt';
                            if (showResult && isCorrectOpt) className += ' correct';
                            if (showResult && isSelected && !isCorrectOpt) className += ' wrong';
                            return (
                                <div key={key} className={className}
                                    onClick={() => revealed && clickable && phase === 'question' && handleAnswer(key)}
                                    style={{ opacity: revealed ? 1 : 0, transform: revealed ? 'translateY(0)' : 'translateY(8px)', transition: 'all 0.3s ease', pointerEvents: revealed && clickable && phase === 'question' ? 'auto' : 'none', cursor: revealed && clickable && phase === 'question' ? 'pointer' : 'default' }}>
                                    <div className="v3-quiz-badge" style={{ width: 28, height: 28, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, flexShrink: 0, background: showResult && isCorrectOpt ? 'var(--v3-grn)' : showResult && isSelected && !isCorrectOpt ? 'var(--v3-rose)' : 'transparent', color: showResult && (isCorrectOpt || (isSelected && !isCorrectOpt)) ? '#000' : 'var(--v3-w)' }}>
                                        {key.toUpperCase()}
                                    </div>
                                    <div style={{ fontSize: 16, lineHeight: 1.5 }}>{text}</div>
                                </div>
                            );
                        })}
                    </div>
                </div>
                {phase === 'explanation' && q.explanation && (
                    <div style={{ marginTop: 20, padding: '14px 18px', borderRadius: 10, background: 'rgba(126, 231, 135, 0.08)', border: '1px solid rgba(126, 231, 135, 0.2)', fontSize: 15, lineHeight: 1.6, color: 'var(--v3-w)' }}>
                        <div style={{ fontSize: 11, color: 'var(--v3-grn)', fontFamily: "'JetBrains Mono', monospace", marginBottom: 6, letterSpacing: '0.1em' }}>EXPLANATION</div>
                        {q.explanation}
                    </div>
                )}
            </div>
            <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                <button className="v3-nb" onClick={onPrevSection} style={{ fontSize: 12 }}>← PREV</button>
                <button className="v3-nb" onClick={onNextSection} style={{ fontSize: 12 }}>SKIP →</button>
            </div>
        </div>
    );
};
