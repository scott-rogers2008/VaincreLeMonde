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

    def call_local_llm(self, prompt: str) -> tuple[str, str]:
        """
        Synchronous connection to Ollama. 
        Guarantees extraction of reasoning paths even when <think> tags are omitted.
        """
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
                raw_res = json.loads(response.read().decode('utf-8'))["response"]
                
                # Fallback Strategy A: Standard tag matching
                thinking = ""
                think_match = re.search(r'<think>(.*?)</think>', raw_res, re.DOTALL)
                if think_match:
                    thinking = think_match.group(1).strip()
                    return raw_res, thinking
                
                # Fallback Strategy B: Code block interception
                json_start = raw_res.find("```json")
                if json_start != -1:
                    thinking = raw_res[:json_start].strip()
                    return raw_res, thinking
                
                # Fallback Strategy C: Bracket interception
                bracket_start = raw_res.find("{")
                if bracket_start != -1:
                    thinking = raw_res[:bracket_start].strip()
                    return raw_res, thinking
                
                return raw_res, "No clear boundaries detected in output stream."
        except Exception as e:
            return f'{{"error": "LLM Execution Fail: {str(e)}"}}', f"Network error: {str(e)}"

    def parse_json_block(self, text: str) -> dict:
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
                # Strip raw returns inside unescaped strings that break standard parsers
                sanitized_str = json_str.replace("\n", " ").replace("'", '"')
                return json.loads(sanitized_str.strip())
            except Exception:
                return {}

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, pillar: str, data_context: str) -> str:
        synthesis_prompt = f"""You are TutorBot, speaking from the [{pillar}] sector of the Life Matrix.
You must construct your reply strictly using the verified document facts provided in the Context Base.
Pedagogical Target: {pedagogical_intent}
Context Base: {data_context}
Query: {user_query}
"""
        res, _ = self.call_local_llm(synthesis_prompt)
        return res
