#!/usr/bin/env python3
"""
scan_bad_avatars.py

Scans all jobs and produces a readable report of avatar videos
that were generated with reference audio (30s duration) instead of TTS.

Usage:
  python3 scan_bad_avatars.py
  python3 scan_bad_avatars.py --jobs-dir player/jobs --tolerance 1.5
"""

import os
import json
import subprocess
import argparse
from datetime import datetime

JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player", "jobs")
REFERENCE_DURATION = 30.0
DEFAULT_TOLERANCE = 1.5
DEFAULT_MIN_TEXT_LEN = 100


def get_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def get_text(section):
    narr = section.get("narration", "")
    if isinstance(narr, dict):
        return narr.get("full_text", "")
    return str(narr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs-dir", default=JOBS_DIR)
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    parser.add_argument("--min-text-len", type=int, default=DEFAULT_MIN_TEXT_LEN)
    parser.add_argument("--output", default="bad_avatars_report.txt",
                        help="Output report file (default: bad_avatars_report.txt)")
    args = parser.parse_args()

    print(f"🔍 Scanning {args.jobs_dir} ...")

    bad = {}  # job_id -> list of section info
    job_names = sorted(os.listdir(args.jobs_dir))

    for i, job_id in enumerate(job_names):
        job_dir = os.path.join(args.jobs_dir, job_id)
        pres_path = os.path.join(job_dir, "presentation.json")
        if not os.path.isdir(job_dir) or not os.path.exists(pres_path):
            continue

        try:
            pres = json.load(open(pres_path, encoding="utf-8"))
        except Exception:
            continue

        for sec in pres.get("sections", []):
            if sec.get("avatar_status") != "completed":
                continue
            av_rel = sec.get("avatar_video", "")
            if not av_rel:
                continue
            av_path = os.path.join(job_dir, av_rel)
            if not os.path.exists(av_path):
                continue

            text = get_text(sec)
            if len(text.strip()) < args.min_text_len:
                continue

            dur = get_duration(av_path)
            if dur is None:
                continue

            if abs(dur - REFERENCE_DURATION) <= args.tolerance:
                bad.setdefault(job_id, []).append({
                    "section_id": sec.get("section_id"),
                    "duration": round(dur, 1),
                    "text_len": len(text),
                    "text_preview": text[:80].replace("\n", " "),
                })

        if (i + 1) % 20 == 0:
            print(f"  ... {i+1}/{len(job_names)} jobs scanned, {sum(len(v) for v in bad.values())} bad sections so far")

    total_sections = sum(len(v) for v in bad.values())
    total_jobs = len(bad)

    # ── Write report ────────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("BAD AVATAR VIDEOS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total affected jobs   : {total_jobs}")
    lines.append(f"Total bad sections    : {total_sections}")
    lines.append(f"Detection threshold  : duration ≈ {REFERENCE_DURATION}s ± {args.tolerance}s")
    lines.append("=" * 70)
    lines.append("")

    for job_id, sections in sorted(bad.items()):
        lines.append(f"JOB: {job_id}  ({len(sections)} section(s))")
        lines.append("-" * 70)
        for s in sections:
            lines.append(
                f"  Section {s['section_id']:>3} | dur={s['duration']}s | "
                f"text={s['text_len']}chars | {s['text_preview']}..."
            )
        lines.append("")

    report_text = "\n".join(lines)

    # Print to console (summary)
    print()
    print(f"{'='*70}")
    print(f"✅ Scan complete: {total_sections} bad sections in {total_jobs} jobs")
    print(f"{'='*70}")
    for job_id, sections in list(sorted(bad.items()))[:20]:
        sec_ids = [str(s['section_id']) for s in sections]
        print(f"  {job_id}: sections {', '.join(sec_ids)}")
    if total_jobs > 20:
        print(f"  ... and {total_jobs - 20} more jobs")

    # Save report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\n📄 Full report saved: {report_path}")

    # Also save JSON for programmatic use
    json_path = report_path.replace(".txt", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_jobs": total_jobs,
            "total_sections": total_sections,
            "jobs": {job_id: sections for job_id, sections in sorted(bad.items())}
        }, f, indent=2)
    print(f"📄 JSON report saved : {json_path}")


if __name__ == "__main__":
    main()
