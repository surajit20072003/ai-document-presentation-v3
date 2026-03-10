# Read-only variant of repair_metadata - for sanity checker UI
@app.route("/api/sanity-report/<job_id>", methods=["GET"])
def sanity_report(job_id):
    """
    Returns comprehensive truth report about job assets (READ-ONLY).
    Scans disk vs JSON and returns detailed diff without modifying anything.
    """
    try:
        job_dir = JOBS_DIR / job_id
        pres_path = job_dir / "presentation.json"
        video_dir = job_dir / "videos"
        avatar_dir = job_dir / "avatars"
        images_dir = job_dir / "images"
        
        if not pres_path.exists():
            return jsonify({"error": "Job presentation.json not found"}), 404
        
        # Load presentation.json
        with open(pres_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Scan directories
        found_videos = []
        if video_dir.exists():
            found_videos = [f.name for f in video_dir.iterdir() if f.is_file() and f.suffix == ".mp4"]
        
        found_avatars = []
        if avatar_dir.exists():
            found_avatars = [f.name for f in avatar_dir.iterdir() if f.is_file() and f.suffix == ".mp4"]
        
        found_images = []
        if images_dir.exists():
            found_images = [f.name for f in images_dir.iterdir() if f.is_file() and f.suffix in [".png", ".jpg", ".jpeg"]]
        
        # Extract all references from JSON
        json_videos = set()
        json_avatars = set()
        json_images = set()
        section_details = []
        
        for section in data.get("sections", []):
            sid = str(section.get("section_id"))
            section_info = {
                "section_id": sid,
                "section_type": section.get("section_type"),
                "title": section.get("title"),
                "renderer": section.get("renderer"),
                "videos_on_disk": [],
                "videos_in_json": [],
                "videos_orphaned": [],
                "videos_missing": [],
                "avatar_status": "unknown",
                "segments_with_beats": 0,
                "total_beat_videos": 0
            }
            
            # Check section-level video_path
            video_path = section.get("video_path", "")
            if video_path:
                filename = Path(video_path).name
                json_videos.add(filename)
                section_info["videos_in_json"].append(filename)
            
            # Check beat_videos array (section-level)
            beat_videos = section.get("beat_videos", [])
            for bv in beat_videos:
                if bv:
                    filename = Path(bv).name
                    json_videos.add(filename)
                    section_info["videos_in_json"].append(filename)
            
            # CRITICAL: Check narration.segments[].beat_videos (segment-level)
            narration = section.get("narration", {})
            segments = narration.get("segments", [])
            for seg in segments:
                seg_beat_videos = seg.get("beat_videos", [])
                if seg_beat_videos:
                    section_info["segments_with_beats"] += 1
                    for sbv in seg_beat_videos:
                        if sbv:
                            filename = Path(sbv).name
                            json_videos.add(filename)
                            section_info["videos_in_json"].append(filename)
                            section_info["total_beat_videos"] += 1
            
            # Check video_prompts for expected files
            video_prompts = section.get("video_prompts", [])
            render_spec = section.get("render_spec", {})
            if not video_prompts:
                video_prompts = render_spec.get("video_prompts", [])
            
            # Check recap_video_paths
            recap_paths = section.get("recap_video_paths", [])
            for rp in recap_paths:
                if rp:
                    filename = Path(rp).name
                    json_videos.add(filename)
                    section_info["videos_in_json"].append(filename)
            
            # Check avatar
            avatar_path = section.get("avatar_video", "")
            if avatar_path:
                filename = Path(avatar_path).name
                json_avatars.add(filename)
                if filename in found_avatars:
                    section_info["avatar_status"] = "found"
                else:
                    section_info["avatar_status"] = "missing"
            else:
                section_info["avatar_status"] = "not_referenced"
            
            # Find videos on disk for this section
            section_video_pattern = f"topic_{sid}"
            section_videos_on_disk = [v for v in found_videos if v.startswith(section_video_pattern)]
            section_info["videos_on_disk"] = section_videos_on_disk
            
            # Determine orphaned vs missing
            for vod in section_videos_on_disk:
                if vod not in section_info["videos_in_json"]:
                    section_info["videos_orphaned"].append(vod)
            
            for vij in section_info["videos_in_json"]:
                if vij not in found_videos:
                    section_info["videos_missing"].append(vij)
            
            section_details.append(section_info)
        
        # Global orphaned/missing files
        orphaned_videos = [v for v in found_videos if v not in json_videos]
        missing_videos = [v for v in json_videos if v not in found_videos]
        
        orphaned_avatars = [a for a in found_avatars if a not in json_avatars]
        missing_avatars = [a for a in json_avatars if a not in found_avatars]
        
        # Calculate accuracy
        total_on_disk = len(found_videos) + len(found_avatars)
        total_referenced = len(json_videos) + len(json_avatars)
        matched = len(json_videos & set(found_videos)) + len(json_avatars & set(found_avatars))
        
        accuracy = 100.0
        if total_referenced > 0:
            accuracy = (matched / total_referenced) * 100
        
        return jsonify({
            "job_id": job_id,
            "accuracy": round(accuracy, 2),
            "summary": {
                "videos_on_disk": len(found_videos),
                "videos_in_json": len(json_videos),
                "avatars_on_disk": len(found_avatars),
                "avatars_in_json": len(json_avatars),
                "images_on_disk": len(found_images),
                "orphaned_videos": len(orphaned_videos),
                "missing_videos": len(missing_videos),
                "matched_videos": len(json_videos & set(found_videos))
            },
            "orphaned": {
                "videos": orphaned_videos,
                "avatars": orphaned_avatars
            },
            "missing": {
                "videos": missing_videos,
                "avatars": missing_avatars
            },
            "sections": section_details
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
