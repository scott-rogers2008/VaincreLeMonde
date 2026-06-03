# src/agentic/codebase_guru/tools/embedder.py

import urllib.request
import json

class LocalEmbedder:
    def __init__(self, model_name="nomic-embed-text", host="http://localhost:11434"):
        self.model_name = model_name
        self.api_url = f"{host}/api/embeddings"

    def _chunk_text_sliding_window(self, text: str, max_chars: int = 4000, overlap: int = 800) -> list:
        """Splits text into overlapping chunks so 100% of the data is preserved."""
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]
            
            # Append contextual markers if it's a continuing chunk
            if start > 0:
                chunk = "... [Context Continuation] ...\n" + chunk
            if end < len(text):
                chunk = chunk + "\n... [Context Continues Below] ..."
                
            chunks.append(chunk)
            start += (max_chars - overlap) # Shift forward leaving an overlap buffer
            
        return chunks

    def get_embeddings_for_piece(self, text: str) -> list:
        """
        Processes text completely by chunking it if necessary, requesting vectors 
        for all parts, and returning a list of vector objects.
        """
        if not text or not text.strip():
            return []

        # Safely chunk text using an optimal sliding scale configuration
        text_chunks = self._chunk_text_sliding_window(text, max_chars=4000, overlap=800)
        vector_results = []

        for idx, chunk_text in enumerate(text_chunks):
            payload = {
                "model": self.model_name,
                "prompt": chunk_text
            }
            try:
                json_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                req = urllib.request.Request(
                    self.api_url, 
                    data=json_bytes, 
                    headers={'Content-Type': 'application/json; charset=utf-8'}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    vector_results.append({
                        "chunk_index": idx,
                        "chunk_text": chunk_text,
                        "vector": res_data["embedding"]
                    })
            except Exception as e:
                print(f"❌ Failed chunk generation pass: {e}")
                
        return vector_results
