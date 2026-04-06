import { BADGE_CONFIG } from './constants';
import { getSectionType } from './utils';
import type { V3Section } from './types';

interface V3SectionsPanelProps {
    sections: V3Section[];
    currentIndex: number;
    onSectionClick: (index: number) => void;
    onClose: () => void;
}

export const V3SectionsPanel = ({ sections, currentIndex, onSectionClick, onClose }: V3SectionsPanelProps) => (
    <div className="v3-sections-panel" onClick={(e) => e.stopPropagation()}>
        <div className="v3-sp-header">
            <span className="v3-sp-title">Sections</span>
            <button className="v3-sp-close" onClick={onClose}>✕</button>
        </div>
        <div className="v3-sp-list">
            {sections.map((sec, i) => {
                const secType = getSectionType(sec);
                const badge = BADGE_CONFIG[secType] || BADGE_CONFIG.content;
                const isActive = i === currentIndex;
                const dur = sec.narration?.total_duration_seconds || sec.segment_duration_seconds || sec.dur;
                const durStr = dur ? `${Math.floor(dur / 60)}:${String(Math.floor(dur % 60)).padStart(2, '0')}` : '';
                return (
                    <button key={String(sec.section_id)} className={`v3-sp-item ${isActive ? 'active' : ''}`}
                        onClick={() => { onSectionClick(i); onClose(); }}>
                        <span className="v3-sp-idx">{i + 1}</span>
                        <span className="v3-sp-info">
                            <span className="v3-sp-name">{sec.title || `Section ${i + 1}`}</span>
                            <span className="v3-sp-meta">
                                <span className="v3-sp-badge" style={{ background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}>
                                    {badge.label}
                                </span>
                                {durStr && <span className="v3-sp-dur">{durStr}</span>}
                            </span>
                        </span>
                    </button>
                );
            })}
        </div>
    </div>
);
