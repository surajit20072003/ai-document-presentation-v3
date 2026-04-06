/**
 * utils.ts — PATCHED: removed V3_PROXY_BASE.
 * getMediaSrc now builds direct /player/jobs/{jobId}/ URLs (same as dashboard.html).
 */

/**
 * Resolve a relative media path to a direct job URL.
 * e.g. "avatars/section_1.mp4" → "/player/jobs/abc123/avatars/section_1.mp4"
 */
export function getMediaSrc(path: string, jobId: string): string {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:')) {
        return path;
    }
    // Already an absolute path on the server
    if (path.startsWith('/')) return path;
    return `/player/jobs/${jobId}/${path}`;
}

/** HTML-escape a string */
export function escapeHtml(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/** Get the section type string from a section */
export function getSectionType(section: { section_type?: string; type?: string }): string {
    return section.section_type || section.type || 'content';
}

/** Get avatar video URL from a section (tries multiple fields) */
export function getAvatarUrl(section: {
    avatar_video?: string;
    avatar_url?: string;
    avatar?: string;
    b2_url?: string;
}): string {
    return section.avatar_video || section.avatar_url || section.avatar || section.b2_url || '';
}
