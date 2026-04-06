import { useKaraokeEngine } from './hooks/useKaraokeEngine';
import type { V3Section, SubtitleMode } from './types';

interface V3SubtitlesProps {
    section: V3Section | null;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
    mode: SubtitleMode;
}

export const V3Subtitles = ({ section, avatarVideoRef, mode }: V3SubtitlesProps) => {
    const { words, activeWordIndex, activeSentenceIndex } = useKaraokeEngine({ section, avatarVideoRef });
    if (mode === 'off' || words.length === 0) return null;

    const sentenceWords = activeSentenceIndex >= 0
        ? words.filter((w) => w.sentenceIdx === activeSentenceIndex)
        : words.slice(0, Math.min(20, words.length));

    if (sentenceWords.length === 0) return null;
    const sectionType = section?.section_type || section?.type || '';
    const isIntro = sectionType === 'intro';

    return (
        <div className={`v3-subtitle-overlay ${isIntro ? 'v3-subtitle-overlay--fullscreen' : ''}`}>
            {sentenceWords.map((w, i) => {
                const globalIdx = words.indexOf(w);
                let cls = 'v3-sub-word future';
                if (mode === 'full') {
                    cls = 'v3-sub-word spoken';
                } else if (mode === 'karaoke') {
                    if (globalIdx < activeWordIndex) cls = 'v3-sub-word spoken';
                    else if (globalIdx === activeWordIndex) cls = 'v3-sub-word active';
                    else cls = 'v3-sub-word future';
                }
                return <span key={`${w.sentenceIdx}-${i}`} className={cls}>{w.text}{' '}</span>;
            })}
        </div>
    );
};
