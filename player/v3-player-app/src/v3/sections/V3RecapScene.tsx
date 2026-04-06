import type { V3Section } from '../types';

// Bug 2 Fix: return null — recap sections carry their visual weight via
// avatar + video background + subtitles only. Text overlay overlaps video.
interface V3RecapSceneProps {
    section: V3Section;
    avatarVideoRef: React.RefObject<HTMLVideoElement | null>;
}
export const V3RecapScene = ({ section: _, avatarVideoRef: _r }: V3RecapSceneProps) => null;
