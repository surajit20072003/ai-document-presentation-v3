import json

def list_renderer_choices(json_file):
    try:
        with open(json_file, 'r', encoding='utf-16') as f:
            data = json.load(f)
    except:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

    choices = data.get('decision_log', {}).get('renderer_choices', [])
    for choice in choices:
        print(f"ID: {choice.get('section_id')}, Renderer: {choice.get('renderer')}")

if __name__ == "__main__":
    list_renderer_choices('local_job_aa400742_presentation.json')
