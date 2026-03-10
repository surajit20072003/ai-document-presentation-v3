from pathlib import Path

path = Path(r"c:\Users\email\Downloads\AI-Document-presentation\ai-doc-presentation\player\jobs\603bd693\source_markdown.md")

try:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"--- File Read Success ({len(content)} chars) ---")
    
    # 1. Look for "Example"
    print("\n=== SEARCHING FOR 'Example' ===")
    parts = content.split("Example")
    if len(parts) > 1:
        # Show the first found example context
        snippet = "Example" + parts[1][:500]
        print(snippet)
    else:
        print("No explicit 'Example' keyword found.")

    # 2. Look for "Figure" (often used for visuals)
    print("\n=== SEARCHING FOR 'Figure' ===")
    parts = content.split("Figure")
    if len(parts) > 1:
        snippet = "Figure" + parts[1][:500]
        print(snippet)
    
except Exception as e:
    print(f"Error: {e}")
