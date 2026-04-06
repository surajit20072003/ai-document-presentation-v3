import { useState, useEffect, useRef } from 'react';
import type { V3Section } from '../types';

export interface KaraokeWord {
    text: string;
    start: number;
    end: number;
    sentenceIdx: number;
}

interface UseKaraokeEngineOpts {
    section: V3Section | null;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
}

const LEAD_MS = 80;
const PUNCT_WEIGHTS: Record<string, number> = {
    '.': 8, '!': 8, '?': 8,
    ',': 4, ';': 4, ':': 4,
};

function buildWords(section: V3Section): KaraokeWord[] {
    const segs = section.narration?.segments;
    if (!segs || segs.length === 0) return [];
    const words: KaraokeWord[] = [];
    let sentenceIdx = 0;
    for (const seg of segs) {
        const text = seg.text?.trim();
        if (!text) continue;
        const segStart = seg.start_seconds ?? 0;
        const segEnd = seg.end_seconds ?? (segStart + (seg.duration_seconds || seg.duration || 5));
        const segDur = segEnd - segStart;
        const rawWords = text.split(/\s+/).filter(Boolean);
        if (rawWords.length === 0) continue;
        let totalWeight = 0;
        const weights = rawWords.map((w) => {
            let wt = w.length;
            const last = w[w.length - 1];
            if (PUNCT_WEIGHTS[last]) wt += PUNCT_WEIGHTS[last];
            totalWeight += wt;
            return wt;
        });
        let cumTime = segStart;
        rawWords.forEach((w, i) => {
            const dur = (weights[i] / totalWeight) * segDur;
            words.push({ text: w, start: cumTime - LEAD_MS / 1000, end: cumTime + dur, sentenceIdx });
            cumTime += dur;
            const last = w[w.length - 1];
            if (last === '.' || last === '!' || last === '?') sentenceIdx++;
        });
    }
    return words;
}

export function useKaraokeEngine({ section, avatarVideoRef }: UseKaraokeEngineOpts) {
    const [words, setWords] = useState<KaraokeWord[]>([]);
    const [activeWordIndex, setActiveWordIndex] = useState(-1);
    const epochRef = useRef(0);

    useEffect(() => {
        epochRef.current++;
        setActiveWordIndex(-1);
        if (!section) { setWords([]); return; }
        setWords(buildWords(section));
    }, [section]);

    useEffect(() => {
        const vid = avatarVideoRef.current;
        if (!vid || words.length === 0) return;
        const epoch = epochRef.current;
        const onTime = () => {
            if (epochRef.current !== epoch) return;
            const t = vid.currentTime;
            let idx = -1;
            for (let i = 0; i < words.length; i++) {
                if (t >= words[i].start && t < words[i].end) { idx = i; break; }
                if (t < words[i].start) break;
                idx = i;
            }
            setActiveWordIndex(idx);
        };
        vid.addEventListener('timeupdate', onTime);
        return () => vid.removeEventListener('timeupdate', onTime);
    }, [avatarVideoRef, words]);

    const activeSentenceIndex = activeWordIndex >= 0 ? words[activeWordIndex]?.sentenceIdx ?? -1 : -1;
    return { words, activeWordIndex, activeSentenceIndex };
}
