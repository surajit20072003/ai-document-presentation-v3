import os

def rename_files(video_dir):
    for filename in os.listdir(video_dir):
        if filename.startswith('topic_section_6_') and filename.endswith('.mp4'):
            new_name = filename.replace('topic_section_6_', 'topic_6_')
            old_path = os.path.join(video_dir, filename)
            new_path = os.path.join(video_dir, new_name)
            print(f"Renaming {filename} to {new_name}")
            os.rename(old_path, new_path)

if __name__ == "__main__":
    rename_files(r'c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\48808436\videos')
