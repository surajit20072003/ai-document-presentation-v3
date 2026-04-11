import { useState, useEffect, useRef } from 'react';
import type { V3Section, WordTimestamp } from '../types';

export interface KaraokeWord {
    text: string;
    start: number;
    end: number;
    sentenceIdx: number;
}

interface UseKaraokeEngineOpts {
    section: V3Section | null;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
    overrideText?: string | null;
    /** Exact word timestamps from subtitles.json — overrides character-estimate when provided */
    exactWords?: WordTimestamp[] | null;
}

const LEAD_MS = 80;
const PUNCT_WEIGHTS: Record<string, number> = {
    '.': 8, '!': 8, '?': 8,
    ',': 4, ';': 4, ':': 4,
};

function buildWordsFromText(text: string, segStart: number, segDur: number, startSentenceIdx: number): { words: KaraokeWord[], nextSentenceIdx: number } {
    const words: KaraokeWord[] = [];
    const rawWords = text.trim().split(/\s+/).filter(Boolean);
    let sentenceIdx = startSentenceIdx;
    if (rawWords.length === 0) return { words, nextSentenceIdx: sentenceIdx };

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
    return { words, nextSentenceIdx: sentenceIdx };
}

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
        const res = buildWordsFromText(text, segStart, segDur, sentenceIdx);
        words.push(...res.words);
        sentenceIdx = res.nextSentenceIdx;
    }
    return words;
}

/** Convert exact WordTimestamp[] → KaraokeWord[] (adds sentenceIdx from punctuation) */
function exactToKaraoke(exactWords: WordTimestamp[]): KaraokeWord[] {
    let sentenceIdx = 0;
    return exactWords.map((w) => {
        const kw: KaraokeWord = {
            text: w.word,
            start: w.start,
            end: w.end,
            sentenceIdx,
        };
        const last = w.word.trimEnd().slice(-1);
        if (last === '.' || last === '!' || last === '?') sentenceIdx++;
        return kw;
    });
}

export function useKaraokeEngine({ section, avatarVideoRef, overrideText, exactWords }: UseKaraokeEngineOpts) {
    const [words, setWords] = useState<KaraokeWord[]>([]);
    const [activeWordIndex, setActiveWordIndex] = useState(-1);
    const epochRef = useRef(0);

    useEffect(() => {
        epochRef.current++;
        setActiveWordIndex(-1);

        if (overrideText) {
            const vid = avatarVideoRef.current;
            if (!vid) return;
            const updateWords = () => {
                const dur = vid.duration && isFinite(vid.duration) ? vid.duration : 5;
                setWords(buildWordsFromText(overrideText, 0, dur, 0).words);
            };
            updateWords();
            vid.addEventListener('durationchange', updateWords);
            vid.addEventListener('loadedmetadata', updateWords);
            return () => {
                vid.removeEventListener('durationchange', updateWords);
                vid.removeEventListener('loadedmetadata', updateWords);
            };
        }

        // If exact word timestamps available from subtitles.json → use them
        if (exactWords && exactWords.length > 0) {
            setWords(exactToKaraoke(exactWords));
            return;
        }

        if (!section) { setWords([]); return; }
        setWords(buildWords(section));
    }, [section, overrideText, exactWords]); // avatarVideoRef intentionally omitted — it's a stable ref; .current is read dynamically

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
            // Mirror legacy player: once video has started, always show at least word 0.
            if (idx < 0 && t > 0 && words.length > 0) idx = 0;
            setActiveWordIndex(idx);
        };
        vid.addEventListener('timeupdate', onTime);
        return () => vid.removeEventListener('timeupdate', onTime);
    }, [words]); // avatarVideoRef intentionally omitted — .current is read dynamically at effect run time

    const activeSentenceIndex = activeWordIndex >= 0 ? words[activeWordIndex]?.sentenceIdx ?? -1 : -1;
    return { words, activeWordIndex, activeSentenceIndex };
}
