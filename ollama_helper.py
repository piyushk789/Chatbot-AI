import json
import time
import spacy
import requests
import subprocess

def start_ollama(model: str):
    subprocess.Popen(f'cmd /k "ollama run {model}"')

def get_list_models():
    llama_list = subprocess.run("ollama list", shell=True, capture_output=True, text=True, check=True)
    if not llama_list.returncode:
        ls = [name_line.split(" ")[0] for name_line in llama_list.stdout.splitlines()[1:]]
        if len(ls): return ls
        raise ValueError("Ollama models NOT Found")
    else:
        raise ConnectionError("Ollama not working")

def is_ollama_running():
    try:
        res = requests.get("http://localhost:11434")
        return res.status_code == 200
    except:
        return False

def starter(model: str = "llama3", max_retries: int = 3):
    print("Starting Ollama...")
    model_list = get_list_models()

    if model_list and model not in model_list:
        raise ValueError("Invalid model")

    if not is_ollama_running():
        start_ollama(model)
        print("Ollama process launched. Waiting for it to start...")

    for attempt in range(max_retries):
        print(f"Checking if Ollama is running... attempt {attempt + 1}")
        if is_ollama_running():
            return f"✅ {model} is up and running!\n"
        time.sleep(2)

    return f"❌ {model} failed to start.\n"

def ask_ollama(prompt, /, model, stream):
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": stream},
            stream=stream)

        if stream:
            full_reply = ""
            for line in res.iter_lines():
                if line:
                    part = json.loads(line.decode('utf-8')).get("response", "")
                    full_reply += part
            return full_reply
        else:
            data = res.json()
            return data.get("response", "[No response]")

    except Exception as e:
        return f"[Error: {e}]"

def generate_title(text):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    nouns = [token.text for token in doc if token.pos_ in ['NOUN', 'PROPN']]
    verbs = [token.text for token in doc if token.pos_ == 'VERB']

    keywords = nouns[:2] + verbs[:1]
    title = " ".join(keywords).title()
    return title or "Untitled"


if __name__ == '__main__':
    MODEL = "llama3.2:latest"
