import numpy as np
from smolagents import LiteLLMModel
from sentence_transformers import SentenceTransformer, util

MIN_CHUNK_CHARS = 400   # Don't split too early 
MAX_CHUNK_CHARS = 2000  # Safety valve (~500 tokens)
SIMULARITY_MODEL = 'nomic-ai/nomic-embed-text-v1.5'
CHAT_MODEL = "ollama/glm4-tool:9b"

class SemanticChunker:
    def __init__(self, model_name=SIMULARITY_MODEL, min_chars=MIN_CHUNK_CHARS, max_chars=MAX_CHUNK_CHARS):
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        self.chat_model_name = CHAT_MODEL
        self.min_chars = min_chars
        self.max_chars = max_chars

    def llm_check_semantic_break(self, pre_sentence, post_sentence, chat_model: LiteLLMModel):
        if not pre_sentence.strip() or not post_sentence.strip():
            return False

        prompt = f"""
        You are an expert document architect. Your task is to determine if Section 2 starts a 
        significantly different topic than Section 1.

        Section 1: {pre_sentence}
        Section 2: {post_sentence}

        Think step-by-step:
        1. What is the primary theme of Section 1?
        2. What is the primary theme of Section 2?
        3. Is there a logical transition?

        If it's a new topic, say 'Decision: YES'. If it's a continuation, say 'Decision: NO'.
        """

        for _ in range(2):
            # smolagents models take a list of messages (OpenAI format)
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            response_message = chat_model(messages)
            response = response_message.content.strip().lower()
            
            # Logic to extract the decision
            last_line = response.split('\n')[-1]
            if 'yes' in last_line or 'yes' in response:
                return True
            if 'no' in last_line or 'no' in response[:20]:
                return False
                
        return False

    def chunk_text(self, text, div='\n', sensitivity=0.9):
        paragraphs = [p+div for p in text.split(div) if p.strip()]

        prefixed_section = [f"clustering: {s}" for s in paragraphs]
        sentence_embeddings = self.model.encode(prefixed_section, normalize_embeddings=True, convert_to_tensor=True)
    
        cosine_similarities = []
        for i in range(len(paragraphs) - 1):
            cosine_similarities.append(util.cos_sim(sentence_embeddings[i], sentence_embeddings[i+1]))
    
        chunks = []
        sims = [s.item() for s in cosine_similarities]
        mean_sim = np.mean(sims)
        std_sim = np.std(sims)
        dynamic_threshold = mean_sim - (sensitivity * std_sim)

        chat_model = LiteLLMModel(
            model_id=self.chat_model_name, 
            api_base="http://localhost:11434", # Default Ollama port
            num_ctx=8192                       # Optional: set context window
        )

        current_chunk = [paragraphs[0]]
        for i in range(len(paragraphs) - 1):
            current_len = len("\n".join(current_chunk))
            if current_len > MAX_CHUNK_CHARS:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [paragraphs[i+1]]
            elif current_len > MIN_CHUNK_CHARS:
                if cosine_similarities[i].item() < dynamic_threshold:
                    if self.llm_check_semantic_break("\n".join(current_chunk), paragraphs[i+1], chat_model):
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [paragraphs[i+1]]
                else:
                    current_chunk.append(paragraphs[i+1])
            else:
                current_chunk.append(paragraphs[i+1])

        chunks.append("\n".join(current_chunk))
    
        print(f"{len(chunks)} - chunks detected from {len(paragraphs)} paragraphs")
        return chunks
