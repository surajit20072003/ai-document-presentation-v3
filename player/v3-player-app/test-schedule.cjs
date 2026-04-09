const fs = require('fs');

const json = JSON.parse(fs.readFileSync('/nvme0n1-disk/nvme01/ai-document-presentation-v3/player/jobs/49_37_162_124_79a6d572/presentation.json', 'utf8'));
const section = json.sections.find(s => s.section_type === 'memory_infographic');

const beats = [];
const jobId = '49_37_162_124_79a6d572';

function getMediaSrc(path, j) {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    if (path.startsWith('/')) return path;
    return `/player/jobs/${j}/${path}`;
}

const infos = section.render_spec?.infographic_beats;
if (infos && infos.length > 0) {
    for (const ib of infos) {
        const imgSrc = ib.image_source || ib.image_path;
        if (!imgSrc) continue;
        beats.push({ start: ib.start_seconds || 0, end: ib.end_seconds || 9999, type: 'image', src: getMediaSrc(imgSrc, jobId) });
    }
    beats.sort((a, b) => a.start - b.start);
} else if ((section.section_type === 'memory_infographic' || section.type === 'memory_infographic' || section.section_type === 'recap' || section.type === 'recap') && section.image_path) {
    beats.push({ start: 0, end: 9999, type: 'image', src: getMediaSrc(section.image_path, jobId) });
}

console.log("Memory Infographic Beats:");
console.log(JSON.stringify(beats, null, 2));
