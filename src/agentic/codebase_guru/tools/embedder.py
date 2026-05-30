import urllib.request
import json

class LocalEmbedder:
    def __init__(self, model_name="nomic-embed-text", host="http://localhost:11434"):
        self.model_name = model_name
        self.api_url = f"{host}/api/embeddings"

    def get_embedding(self, text: str) -> list:
        """Sends text to a local Ollama instance and returns a vector list."""
        if not text.strip():
            # Return an empty array if there is no text (e.g., missing docstring)
            return []

        payload = {
            "model": self.model_name,
            "prompt": text
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.api_url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data["embedding"]
        except Exception as e:
            print(f"❌ Ollama connection error: {e}")
            print("Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull nomic-embed-text`).")
            return []

if __name__ == "__main__":
    # Quick self-test loop
    embedder = LocalEmbedder()
    vector = embedder.get_embedding("def process_data(x): return x * 2")
    print(f"Generated vector sample! Total dimensions: {len(vector)}")
