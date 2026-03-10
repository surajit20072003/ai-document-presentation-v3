from core.unified_content_generator import UNIFIED_SYSTEM_PROMPT, build_user_prompt
import os

# Ensure core module is importable (running from root)
# Save System Prompt
with open("core/prompts/unified_system_prompt_CURRENT.txt", "w", encoding="utf-8") as f:
    f.write(UNIFIED_SYSTEM_PROMPT)

# Save User Prompt Template (Simulation)
dummy_content = "[MARKDOWN CONTENT HERE]"
# Pass raw placeholders to see the structure
user_prompt = build_user_prompt(dummy_content, "{subject}", "{grade}", "{images_list}")

with open("core/prompts/unified_user_template_CURRENT.txt", "w", encoding="utf-8") as f:
    f.write(user_prompt)

print("Prompts extracted to core/prompts/")
