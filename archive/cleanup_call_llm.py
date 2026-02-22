import os

file_path = r"c:\gaboda_v1.3\llm_resource\itinerary_llm_draft\llm_client_draft.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace all occurrences of the fallback return
old_line = 'return json.dumps(_mock_itinerary_from_prompt(prompt), ensure_ascii=False)'
new_line = 'return None'

new_content = content.replace(old_line, new_line)

# Also update the final fallback print message to be accurate
new_content = new_content.replace(
    'print("[LLM] Final fallback: using mock generator")',
    'print("[LLM] Final fallback: returning None")'
)

if old_line not in content:
    print("Warning: Old line not found!")
else:
    print(f"Replaced {content.count(old_line)} occurrences.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)
