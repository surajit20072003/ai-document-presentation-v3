"""
Script to insert the sanity_report endpoint into app.py at the correct location.
"""
from pathlib import Path

# Read the endpoint code
endpoint_file = Path("api/sanity_report_endpoint.py")
endpoint_code = endpoint_file.read_text(encoding='utf-8')

# Read app.py
app_file = Path("api/app.py")
app_content = app_file.read_text(encoding='utf-8')

# Find the location to insert (after repair_metadata function)
insert_marker = 'return jsonify({"status": "error", "error": str(e)}), 500\n\n\n@app.route'
marker_pos = app_content.find(insert_marker)

if marker_pos == -1:
    print("ERROR: Could not find insertion marker")
    exit(1)

# Calculate insertion point (after the first newline sequence)
insert_pos = marker_pos + len('return jsonify({"status": "error", "error": str(e)}), 500\n\n')

# Insert the code
new_content = (
    app_content[:insert_pos] +
    "\n" + endpoint_code + "\n" +
    app_content[insert_pos:]
)

# Write back
app_file.write_text(new_content, encoding='utf-8')
print(f"✓ Successfully inserted sanity_report endpoint at position {insert_pos}")
print(f"✓ New file size: {len(new_content)} bytes (was {len(app_content)})")
