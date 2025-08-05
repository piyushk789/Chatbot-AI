import json
import os
from datetime import datetime

MEMORY_DIR = "memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

def save_memory(model_name, user_msg, bot_reply):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "time": time,
        "model": model_name,
        "user": user_msg,
        "bot": bot_reply
    }

    # Save to model-specific memory
    model_file = os.path.join(MEMORY_DIR, f"{model_name}.json")
    append_to_file(model_file, data)

    # Save to all models memory
    all_file = os.path.join(MEMORY_DIR, "all_models.json")
    append_to_file(all_file, data)

def append_to_file(file_path, data):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            chat = json.load(f)
    else:
        chat = []

    chat.append(data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(chat, f, indent=2, ensure_ascii=False)

def load_memory(file="all_models.json"):
    path = os.path.join(MEMORY_DIR, file)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# bot_reply = ask_ollama(user_prompt)
# save_memory("llama3", user_prompt, bot_reply)
