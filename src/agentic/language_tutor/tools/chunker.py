# src/agentic/language_tutor/tools/chunker.py
import numpy as np
import requests
import re
import json

MIN_CHUNK_CHARS = 400
MAX_CHUNK_CHARS = 2000
SIMULARITY_MODEL = 'bge-m3'
CHAT_MODEL = "hermes3:8b"  # Clean string variant for native Ollama API routing

class SemanticChunker:
    def __init__(self, model_name=SIMULARITY_MODEL, min_chars=MIN_CHUNK_CHARS, max_chars=MAX_CHUNK_CHARS, ollama_url="http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.ollama_embedding_url = f"{ollama_url}/api/embeddings"
        self.ollama_chat_url = f"{ollama_url}/api/generate"
        self.chat_model_name = CHAT_MODEL
        self.min_chars = min_chars
        self.max_chars = max_chars

    def _clean_text_for_bge(self, text: str) -> str:
        """Strips syntax that causes numerical stability (NaN) 500 crashes in Ollama BGE-M3."""
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\|[\s\-:|]+\|', '', text)
        return " ".join(text.split())

    def _get_embedding(self, text: str) -> np.ndarray:
        """Fetches embedding from Ollama with safety scrubbing to prevent 500 errors."""
        cleaned = self._clean_text_for_bge(text)
        if not cleaned.strip():
            return np.zeros(1024)
        try:
            response = requests.post(
                self.ollama_embedding_url, 
                json={"model": self.model_name, "prompt": cleaned},
                timeout=30
            )
            if response.status_code == 500:
                return np.zeros(1024)
            response.raise_for_status()
            return np.array(response.json()["embedding"])
        except Exception:
            return np.zeros(1024)

    def llm_check_semantic_break(self, pre_sentence, post_sentence):
        """Replaces LiteLLMModel with a direct, headless local Ollama HTTP request."""
        if not pre_sentence.strip() or not post_sentence.strip():
            return False
            
        prompt = f"""
        You are an expert document architect. Your task is to determine if Section 2 starts a significantly different topic than Section 1.
        Section 1: {pre_sentence}
        Section 2: {post_sentence}
        Think step-by-step:
        1. What is the primary theme of Section 1?
        2. What is the primary theme of Section 2?
        3. Is there a logical transition? 
        If it's a new topic, say 'Decision: YES'. If it's a continuation, say 'Decision: NO'.
        """
        
        payload = {
            "model": self.chat_model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 4096
            }
        }
        
        for _ in range(2):
            try:
                response = requests.post(self.ollama_chat_url, json=payload, timeout=60)
                response.raise_for_status()
                response_text = response.json().get("response", "").strip().lower()
                
                last_line = response_text.split('\n')[-1]
                if 'yes' in last_line or 'yes' in response_text:
                    return True
                if 'no' in last_line or 'no' in response_text[:20]:
                    return False
            except Exception:
                return False
        return False

    def chunk_text(self, text, div='\n', sensitivity=0.9):
        paragraphs = [p+div for p in text.split(div) if p.strip()]
        if not paragraphs:
            return []
            
        sentence_embeddings = [self._get_embedding(p) for p in paragraphs]
        cosine_similarities = []
        
        for i in range(len(paragraphs) - 1):
            vec1 = sentence_embeddings[i]
            vec2 = sentence_embeddings[i+1]
            norm1, norm2 = np.linalg.norm(vec1), np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                similarity = 0.0
            else:
                similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            cosine_similarities.append(similarity)
            
        chunks = []
        sims = [s for s in cosine_similarities if s > 0.0]
        
        if not sims:
            mean_sim = 0.5
            std_sim = 0.1
        else:
            mean_sim = np.mean(sims)
            std_sim = np.std(sims)
            
        dynamic_threshold = mean_sim - (sensitivity * std_sim)
        current_chunk = [paragraphs[0]]
        
        for i in range(len(paragraphs) - 1):
            current_len = len("\n".join(current_chunk))
            if current_len > self.max_chars:
                chunks.append("\n".join(current_chunk))
                current_chunk = [paragraphs[i+1]]
            elif current_len > self.min_chars:
                if cosine_similarities[i] < dynamic_threshold or cosine_similarities[i] == 0.0:
                    # Cleaned function signature removes framework dependency
                    if self.llm_check_semantic_break("\n".join(current_chunk), paragraphs[i+1]):
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [paragraphs[i+1]]
                    else:
                        current_chunk.append(paragraphs[i+1])
                else:
                    current_chunk.append(paragraphs[i+1])
            else:
                current_chunk.append(paragraphs[i+1])
                
        chunks.append("\n".join(current_chunk))
        print(f"{len(chunks)} - chunks detected from {len(paragraphs)} paragraphs")
        return chunks
