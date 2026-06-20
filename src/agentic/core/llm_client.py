# src/agentic/core/llm_client.py
import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b"

class LLMClient:
    def __init__(self, model_name: str = MODEL_NAME, url: str = OLLAMA_URL):
        self.model_name = model_name
        self.url = url

    def call_local_llm(self, prompt: str) -> str:
        """Executes a synchronous request to the local Ollama instance."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 8192}
        }
        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            # Retaining the required fallback payload pattern cleanly
            return f'{{"error": "LLM Execution Fail: {str(e)}"}}'

    def parse_json_block(self, text: str) -> dict:
        """
        Extracts and cleans a JSON block from the raw LLM response string.
        Uses greedy structural boundary scanning to prevent inner quote/brace truncation.
        """
        if not text:
            return {}
        
        clean_text = text.strip()
        
        json_match = re.search(r'```json\s*(\{.*\})\s*```', clean_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            bracket_match = re.search(r'(\{.*\})', clean_text, re.DOTALL)
            json_str = bracket_match.group(1) if bracket_match else clean_text
            
        try:
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            try:
                sanitized_str = json_str.replace("'", '"')
                return json.loads(sanitized_str.strip())
            except Exception:
                raise

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, pillar: str, data_context: str) -> str:
        """Synthesizes a response contextualized within a specific Life Matrix Pillar."""
        synthesis_prompt = f"""You are TutorBot, speaking from the [{pillar}] sector of the Life Matrix. You must construct your reply strictly using the verified document facts provided in the Context Base.

Pedagogical Target: {pedagogical_intent}
Context Base: {data_context}

Query: {user_query}
"""
        return self.call_local_llm(synthesis_prompt)
