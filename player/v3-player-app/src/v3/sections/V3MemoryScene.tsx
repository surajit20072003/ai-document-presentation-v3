import { useState, useEffect, useCallback } from 'react';
import type { V3Section, V3Flashcard } from '../types';

interface V3MemorySceneProps {
    section: V3Section;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
}

function getCardData(section: V3Section): { front: string; back: string }[] {
    const fc = section.flashcards;
    if (fc && fc.length > 0) {
        return fc.map((c: V3Flashcard) => ({ front: c.q || c.front || c.question || '', back: c.a || c.back || c.answer || '' }));
    }
    const segs = section.narration?.segments || [];
    return segs.map((s, i) => ({ front: `Card ${i + 1}`, back: s.text?.slice(0, 150) || '' }));
}

export const V3MemoryScene = ({ section, avatarVideoRef }: V3MemorySceneProps) => {
    const cards = getCardData(section);
    const [cardIndex, setCardIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);

    useEffect(() => {
        const vid = avatarVideoRef.current;
        if (!vid || cards.length === 0) return;
        const segments = section.narration?.segments || [];
        const iv = setInterval(() => {
            const t = vid.currentTime;
            let idx = 0, cumulative = 0;
            for (let i = 0; i < cards.length; i++) {
                const seg = segments[i];
                const dur = seg?.duration_seconds || seg?.duration || 8;
                const start = seg?.start_seconds ?? cumulative;
                if (t >= start) {
                    idx = i;
                    const flipPoint = start + dur * 0.45;
                    if (t >= flipPoint && cardIndex === i && !flipped) setFlipped(true);
                }
                cumulative += dur;
            }
            if (idx !== cardIndex) { setCardIndex(idx); setFlipped(false); }
        }, 200);
        return () => clearInterval(iv);
    }, [avatarVideoRef, cards.length, section, cardIndex, flipped]);

    const handleFlip = useCallback(() => setFlipped(f => !f), []);
    const handlePrev = useCallback(() => { setCardIndex(i => Math.max(0, i - 1)); setFlipped(false); }, []);
    const handleNext = useCallback(() => { setCardIndex(i => Math.min(cards.length - 1, i + 1)); setFlipped(false); }, [cards.length]);

    if (cards.length === 0) return null;
    const card = cards[cardIndex];

    return (
        <div className="v3-card-scene">
            <div className={`v3-card-3d ${flipped ? 'flipped' : ''}`} onClick={handleFlip}>
                <div className="v3-card-face v3-card-front">
                    <div style={{ fontSize: 13, color: 'var(--v3-dim)', marginBottom: 8, fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.1em' }}>TAP TO FLIP</div>
                    <div style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.5 }}>{card.front}</div>
                </div>
                <div className="v3-card-face v3-card-back">
                    <div style={{ fontSize: 16, lineHeight: 1.6, color: 'var(--v3-w)' }}>{card.back}</div>
                </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, marginTop: 16 }}>
                <button className="v3-nb" onClick={handlePrev} disabled={cardIndex === 0} style={{ opacity: cardIndex === 0 ? 0.3 : 1 }}>◀</button>
                <div style={{ display: 'flex', gap: 6 }}>
                    {cards.map((_, i) => (
                        <div key={i} style={{ width: i === cardIndex ? 20 : 8, height: 8, borderRadius: 4, background: i === cardIndex ? 'var(--v3-gold)' : 'rgba(255,255,255,0.15)', transition: 'all 0.3s', cursor: 'pointer' }}
                            onClick={() => { setCardIndex(i); setFlipped(false); }} />
                    ))}
                </div>
                <button className="v3-nb" onClick={handleNext} disabled={cardIndex === cards.length - 1} style={{ opacity: cardIndex === cards.length - 1 ? 0.3 : 1 }}>▶</button>
            </div>
            <div style={{ textAlign: 'center', marginTop: 8, fontSize: 12, color: 'var(--v3-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                {cardIndex + 1} / {cards.length}
            </div>
        </div>
    );
};
