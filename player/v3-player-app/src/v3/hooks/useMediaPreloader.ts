import { useState, useEffect, useRef, useCallback } from 'react';
import { getMediaSrc, getAvatarUrl } from '../utils';
import type { V3Section } from '../types';

const INITIAL_BATCH = 3;
const LOOKAHEAD = 3;

interface CacheProgress {
    loaded: number;
    total: number;
}

function collectSectionMedia(section: V3Section, jobId: string): string[] {
    const urls: string[] = [];
    const seen = new Set<string>();

    const add = (path: string | undefined | null) => {
        if (!path) return;
        const src = getMediaSrc(path, jobId);
        if (src && !seen.has(src)) { seen.add(src); urls.push(src); }
    };

    add(getAvatarUrl(section));

    if (section.visual_beats) {
        for (const vb of section.visual_beats) { add(vb.video_path); add(vb.image_source); }
    }
    if (section.beat_video_paths) { for (const p of section.beat_video_paths) add(p); }
    if (section.manim_video_paths) { for (const p of section.manim_video_paths) add(p); }
    add(section.video_path);

    if (section.render_spec?.infographic_beats) {
        for (const ib of section.render_spec.infographic_beats) {
            add(ib.image_source); add(ib.image_path);
        }
    }

    const quizItems = [
        ...(section.questions || []),
        ...(section.understanding_quiz ? [section.understanding_quiz] : []),
    ];
    for (const q of quizItems) {
        if (q.avatar_clips) {
            add(q.avatar_clips.question); add(q.avatar_clips.correct);
            add(q.avatar_clips.wrong); add(q.avatar_clips.explanation);
        }
        if (q.explanation_visual) {
            add(q.explanation_visual.video_path); add(q.explanation_visual.wan_video_path);
            add(q.explanation_visual.image_path); add(q.explanation_visual.image_source);
        }
    }
    return urls;
}

export function useMediaPreloader(sections: V3Section[], currentIndex: number, jobId: string) {
    const blobMapRef = useRef<Map<string, string>>(new Map());
    const preloadedSectionsRef = useRef<Set<number>>(new Set());
    const [initialReady, setInitialReady] = useState(false);
    const [cacheProgress, setCacheProgress] = useState<CacheProgress>({ loaded: 0, total: 0 });
    const mountedRef = useRef(true);

    const fetchAsBlob = useCallback(async (url: string, signal?: AbortSignal, sectionIdx?: number): Promise<boolean> => {
        if (blobMapRef.current.has(url)) return true;
        try {
            const resp = await fetch(url, { signal });
            if (!resp.ok) return false;
            const blob = await resp.blob();
            if (signal?.aborted || !mountedRef.current) return false;
            blobMapRef.current.set(url, URL.createObjectURL(blob));
            return true;
        } catch {
            return false;
        }
    }, []);

    const preloadSection = useCallback(async (index: number, signal?: AbortSignal): Promise<number> => {
        if (index < 0 || index >= sections.length) return 0;
        if (preloadedSectionsRef.current.has(index)) return 0;
        preloadedSectionsRef.current.add(index);
        const urls = collectSectionMedia(sections[index], jobId);
        let fetched = 0;
        const results = await Promise.allSettled(urls.map((u) => fetchAsBlob(u, signal, index)));
        for (const r of results) { if (r.status === 'fulfilled' && r.value) fetched++; }
        return fetched;
    }, [sections, jobId, fetchAsBlob]);

    useEffect(() => {
        if (sections.length === 0) return;
        blobMapRef.current.forEach((url) => URL.revokeObjectURL(url));
        blobMapRef.current.clear();
        preloadedSectionsRef.current.clear();
        setInitialReady(false);

        const ctrl = new AbortController();
        const batchCount = Math.min(INITIAL_BATCH, sections.length);
        let totalAssets = 0;
        for (let i = 0; i < batchCount; i++) {
            totalAssets += collectSectionMedia(sections[i], jobId).length;
        }
        setCacheProgress({ loaded: 0, total: totalAssets });

        let loadedSoFar = 0;
        const run = async () => {
            for (let i = 0; i < batchCount; i++) {
                if (ctrl.signal.aborted) return;
                const urls = collectSectionMedia(sections[i], jobId);
                preloadedSectionsRef.current.add(i);
                for (const url of urls) {
                    if (ctrl.signal.aborted) return;
                    await fetchAsBlob(url, ctrl.signal, i);
                    loadedSoFar++;
                    if (mountedRef.current) setCacheProgress({ loaded: loadedSoFar, total: totalAssets });
                }
            }
            if (mountedRef.current && !ctrl.signal.aborted) setInitialReady(true);
        };
        run();
        return () => ctrl.abort();
    }, [sections, jobId, fetchAsBlob]);

    useEffect(() => {
        if (!initialReady || sections.length === 0) return;
        const ctrl = new AbortController();
        const run = async () => {
            for (let i = currentIndex + 1; i <= currentIndex + LOOKAHEAD && i < sections.length; i++) {
                if (ctrl.signal.aborted) return;
                await preloadSection(i, ctrl.signal);
            }
        };
        run();
        return () => ctrl.abort();
    }, [currentIndex, initialReady, sections.length, preloadSection]);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            blobMapRef.current.forEach((url) => URL.revokeObjectURL(url));
            blobMapRef.current.clear();
        };
    }, []);

    const getBlob = useCallback((src: string): string | null => {
        return blobMapRef.current.get(src) || null;
    }, []);

    return { getBlob, initialReady, cacheProgress };
}
