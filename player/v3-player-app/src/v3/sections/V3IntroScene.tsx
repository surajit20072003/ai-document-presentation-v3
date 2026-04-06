import type { V3Section } from '../types';

// Bug 2 Fix: return null — intro sections carry their visual weight via
// avatar + video background + subtitles only. Text overlay overlaps video.
interface V3IntroSceneProps { section: V3Section; }
export const V3IntroScene = ({ section: _ }: V3IntroSceneProps) => null;
