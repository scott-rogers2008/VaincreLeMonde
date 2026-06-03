# src/agentic/codebase_guru/agents/exploration_agent.py

# This agent is designed to explore a codebase using a Neo4j Vector Graph and a set of tools. 
# It interacts with the Ollama API to generate structured outputs that guide its exploration process. 
# The agent is resilient to parsing issues and includes detailed diagnostics for network interactions and response handling.

import json
import urllib.request
import re
from tools.agent_tools import AgentTools

class DeepSeekR1Agent:
    def __init__(self, model_name="deepseek-r1:14b", ollama_host="http://localhost:11434"):
        self.tools = AgentTools()
        self.model_name = model_name
        self.api_url = f"{ollama_host}/api/generate"

    def _call_ollama(self, prompt: str) -> str:
        """Calls Ollama while restricting context and printing network diagnostics."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_ctx": 8192  # Protects your 12GB VRAM
            }
        }
        data = json.dumps(payload).encode('utf-8')
        
        print(f"📡 Connecting to endpoint: {self.api_url}...")
        print(f"🤖 Requesting model: '{self.model_name}'...")
        
        req = urllib.request.Request(
            self.api_url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            # We add a 30-second timeout to prevent infinite freezes
            with urllib.request.urlopen(req, timeout=300) as response:
                status_code = response.getcode()
                print(f"📥 Server responded with status code: {status_code}")
                raw_data = response.read().decode('utf-8')
                return json.loads(raw_data)["response"]
                
        except urllib.error.HTTPError as e:
            print(f"❌ Ollama returned an HTTP Error Code: {e.code}")
            print(f"💡 Reason: {e.read().decode('utf-8')}")
            return ""
        except urllib.error.URLError as e:
            print(f"❌ Network Error: Cannot reach the Ollama server.")
            print(f"💡 Detail: {e.reason}")
            print("👉 Is Ollama actually running? Try running `ollama serve` in your terminal.")
            return ""
        except Exception as e:
            print(f"❌ Unexpected connection failure: {e}")
            return ""

    def execute_step(self, task: str, execution_history: str = "") -> dict:
        """Runs a single tool selection step with resilient parsing loops."""
        
        prompt = f"""
        You are the codebase execution brain of CodebaseGuru.
        You have access to a Neo4j Vector Graph of our local codebase.

        [AVAILABLE TOOLS]
        1. search_semantic_code(user_query) - Vector searches function bodies. Use simple concept terms like 'database connection'.
        2. check_documentation_history(method_name) - Traces version history/drift. Argument must be a single raw function name string.
        3. list_file_contents(file_path) - Maps all methods inside a specific file. Argument must be a valid directory file path like 'tools/parser.py'.

        [OBJECTIVE]
        {task}

        [PREVIOUS EXECUTION STEPS]
        {execution_history if execution_history else "No steps taken yet."}

        [CRITICAL OUTPUT RULES]
        You must specify your next structural move. 
        Your response must include a valid JSON code block matching one of these shapes:

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
        
        # 1. Resilient Thinking Block Extraction
        thinking_process = "No explicit thinking block returned."
        thinking_match = re.search(r'<think>(.*?)</think>', raw_response, re.DOTALL)
        if thinking_match:
            thinking_process = thinking_match.group(1).strip()
        else:
            # If Ollama stripped the tags, everything before the json block is the thinking process
            json_start_idx = raw_response.find("```json")
            if json_start_idx != -1:
                thinking_process = raw_response[:json_start_idx].strip()

        # 2. Resilient JSON Block Extraction
        # Look for the markdown code block first
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        json_str = None
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback: Find raw brackets if the model forgot markdown wrapper blocks
            bracket_match = re.search(r'(\{.*?\})', raw_response, re.DOTALL)
            if bracket_match:
                json_str = bracket_match.group(1)

        if json_str:
            try:
                # Clean common trailing or hidden characters out before decoding
                clean_json_str = json_str.strip().replace("\n", " ")
                action = json.loads(clean_json_str)
                return {"thinking": thinking_process, "action": action}
            except json.JSONDecodeError:
                pass
                
        # Return fallback state to trigger the prompter escalation file if parsing fails
        return {
            "thinking": thinking_process,
            "action": {"status": "FAIL", "raw_output": raw_response}
        }
