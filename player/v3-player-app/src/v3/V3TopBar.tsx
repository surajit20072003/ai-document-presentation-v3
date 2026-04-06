import { BADGE_CONFIG } from './constants';
import { getSectionType } from './utils';
import type { V3Section } from './types';

interface V3TopBarProps {
    title: string;
    sections: V3Section[];
    currentIndex: number;
    onSectionClick: (index: number) => void;
    onClose: () => void;
    isMobile?: boolean;
}

export const V3TopBar = ({ title, sections, currentIndex, onSectionClick, onClose, isMobile }: V3TopBarProps) => {
    const currentSection = sections[currentIndex];
    const sectionType = currentSection ? getSectionType(currentSection) : 'content';
    const badge = BADGE_CONFIG[sectionType] || BADGE_CONFIG.content;

    return (
        <div className="v3-topbar">
            <button className="v3-close-btn" onClick={onClose} title="Close">✕</button>
            <div
                className="v3-tb-badge"
                style={{ background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}
            >
                {badge.label}
            </div>
            <div className="v3-tb-title">{title}</div>
            {!isMobile && currentSection && <div className="v3-tb-sec-name">/ {currentSection.title}</div>}
            <div className="v3-tb-dots">
                {sections.map((_, i) => (
                    <div
                        key={i}
                        className={`v3-tb-dot ${i < currentIndex ? 'past' : i === currentIndex ? 'cur' : 'future'}`}
                        onClick={() => onSectionClick(i)}
                        title={sections[i]?.title || ''}
                    />
                ))}
            </div>
        </div>
    );
};
