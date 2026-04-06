// constants.ts — PATCHED: No V3_PROXY_BASE, no Supabase

export const SPEED_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

export const BADGE_CONFIG: Record<string, { bg: string; color: string; border: string; label: string }> = {
    intro: { bg: 'rgba(246,196,78,0.15)', color: '#f6c44e', border: 'rgba(246,196,78,0.25)', label: 'INTRO' },
    content: { bg: 'rgba(0,210,180,0.12)', color: '#00d2b4', border: 'rgba(0,210,180,0.2)', label: 'CONTENT' },
    summary: { bg: 'rgba(121,192,255,0.12)', color: '#79c0ff', border: 'rgba(121,192,255,0.2)', label: 'SUMMARY' },
    memory: { bg: 'rgba(255,107,138,0.12)', color: '#ff6b8a', border: 'rgba(255,107,138,0.2)', label: 'MEMORY' },
    memory_infographic: { bg: 'rgba(255,107,138,0.12)', color: '#ff6b8a', border: 'rgba(255,107,138,0.2)', label: 'MEMORY' },
    recap: { bg: 'rgba(126,231,135,0.12)', color: '#7ee787', border: 'rgba(126,231,135,0.2)', label: 'RECAP' },
    quiz: { bg: 'rgba(255,107,138,0.12)', color: '#ff6b8a', border: 'rgba(255,107,138,0.2)', label: 'QUIZ' },
    example: { bg: 'rgba(184,169,255,0.12)', color: '#b8a9ff', border: 'rgba(184,169,255,0.2)', label: 'EXAMPLE' },
};
