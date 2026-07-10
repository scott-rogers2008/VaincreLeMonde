# populate_dictionary/eembeddings.py

import requests
from config import OLLAMA_URL, MODEL_NAME

def verify_ollama_status():
    try:
        requests.get("http://localhost:11434/", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Error: Ollama daemon is offline. Run 'ollama run bge-m3'.")
        return False

def get_ollama_embedding(text):
    payload = {"model": MODEL_NAME, "prompt": text}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"\n⚠️ Embedding failed for snippet: '{text[:30]}...'. Error: {e}")
        return None
