import { useState, useEffect } from 'react';
import type { V3Section } from '../types';

interface V3SummarySceneProps {
    section: V3Section;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
}

export const V3SummaryScene = ({ section, avatarVideoRef }: V3SummarySceneProps) => {
    const [visibleCount, setVisibleCount] = useState(0);
    const segments = section.narration?.segments || [];
    const bullets = segments.filter(s => s.purpose !== 'introduce').slice(0, 6).map(s => s.text?.slice(0, 120) || '');

    useEffect(() => {
        const vid = avatarVideoRef.current;
        if (!vid || bullets.length === 0) return;
        const onTime = () => {
            const t = vid.currentTime;
            let count = 0;
            for (let i = 0; i < bullets.length; i++) {
                const seg = segments.filter(s => s.purpose !== 'introduce')[i];
                const threshold = seg?.start_seconds ?? i * 5;
                if (t >= threshold) count = i + 1;
            }
            setVisibleCount(count);
        };
        vid.addEventListener('timeupdate', onTime);
        return () => vid.removeEventListener('timeupdate', onTime);
    }, [avatarVideoRef, bullets.length, segments]);

    if (bullets.length === 0) return null;

    return (
        <div className="v3-summary-scroll" style={{ width: '100%', maxWidth: 520, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, letterSpacing: '0.1em', color: 'var(--v3-dim)', textTransform: 'uppercase' as const, marginBottom: 6 }}>
                By the end of this section, you will…
            </div>
            {bullets.map((text, i) => (
                <div key={i} className={`v3-sbullet ${i < visibleCount ? 'show' : ''}`} style={{ transitionDelay: `${i * 80}ms` }}>
                    <div className="v3-sbullet-n">{i + 1}</div>
                    <div className="v3-sbullet-t">{text}</div>
                </div>
            ))}
        </div>
    );
};
