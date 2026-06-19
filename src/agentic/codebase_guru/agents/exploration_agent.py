# src/agentic/codebase_guru/agents/exploration_agent.py
import json
import urllib.request
import re
from ..tools.agent_tools import AgentTools

class DeepSeekR1Agent:
    def __init__(self, model_name="deepseek-r1:14b", ollama_host="http://localhost:11434"):
        self.tools = AgentTools()
        self.model_name = model_name
        self.api_url = f"{ollama_host}/api/generate"

    def _call_ollama(self, prompt: str) -> str:
        """Calls Ollama while restricting context and protecting system memory configurations."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192
            }
        }
        try:
            json_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.api_url, 
                data=json_bytes, 
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            print(f"❌ Connection failure to Ollama instance: {e}")
            return ""

    def execute_step(self, task: str, execution_history: str = "") -> dict:
        """Runs a single tool selection step with resilient parsing loops."""
        prompt = f"""You are the codebase execution brain of CodebaseGuru operating over a low-memory FalkorDB instance.
You have access to an openCypher vector graph database containing structural blueprints of our local codebase.

[AVAILABLE TOOLS]
1. search_semantic_code(user_query) - Vector searches function bodies. Use simple concept terms like 'database connection'.
2. check_documentation_history(method_name) - Traces version history. Argument must be a single raw function name string.
3. list_file_contents(file_path) - Maps methods in a specific file. Argument must be a forward-slash path like 'tools/parser.py'.

[OBJECTIVE]
{task}

[PREVIOUS EXECUTION STEPS]
{execution_history if execution_history else "No steps taken yet."}

[CRITICAL OUTPUT RULES]
You must specify your next structural move. Your response must include a valid JSON code block matching one of these shapes:
To call a tool:
```json
{{
  "status": "CONTINUE",
  "tool_name": "search_semantic_code",
  "tool_argument": "your target query text"
}}
```
If you have successfully resolved the objective:
```json
{{
  "status": "COMPLETE",
  "final_answer": "Your detailed explanation or structural fix here"
}}
```
"""
        raw_response = self._call_ollama(prompt)
        
        # Extract reasoning steps cleanly
        thinking_process = "No explicit thinking block returned."
        think_match = re.search(r'<think>(.*?)</think>', raw_response, re.DOTALL)
        if think_match:
            thinking_process = think_match.group(1).strip()
        else:
            json_start_idx = raw_response.find("```json")
            if json_start_idx != -1:
                thinking_process = raw_response[:json_start_idx].strip()

        # Isolate target JSON code block structures
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        json_str = json_match.group(1) if json_match else None
        if not json_str:
            bracket_match = re.search(r'(\{.*?\})', raw_response, re.DOTALL)
            if bracket_match:
                json_str = bracket_match.group(1)

        if json_str:
            try:
                clean_json_str = json_str.strip().replace("\n", " ")
                action = json.loads(clean_json_str)
                return {"thinking": thinking_process, "action": action}
            except json.JSONDecodeError:
                pass

        return {
            "thinking": thinking_process,
            "action": {"status": "FAIL", "raw_output": raw_response}
        }
