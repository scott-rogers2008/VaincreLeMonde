# src/agentic/smolagents_chat.py
import os
import json
import re
import urllib.request
from utils import get_git_root
import agentic.tutor_memories as st

# Real tool backends imported directly from your domains
from codebase_guru.tools.agent_tools import AgentTools
from language_tutor.tools.database_tools import db_content_reader, get_language_id
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.user_tools import ask_user_confirmation

BASE_DIR = os.path.abspath(get_git_root(os.curdir))
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "ollama/qwen3.5:9b"  # Optimally mapped for structured extraction

class TutorBotEngine:
    def __init__(self):
        self.code_tools = AgentTools()
        
    def _call_local_llm(self, prompt: str) -> str:
        """Low-level robust local LLM execution with strict context ceiling protection."""
        payload = {
            "model": MODEL_NAME.replace("ollama/", ""),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2, 
                "num_ctx": 8192
            }
        }
        try:
            req = urllib.request.Request(
                OLLAMA_URL, 
                data=json.dumps(payload).encode('utf-8'), 
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            return f"{{\"error\": \"LLM Execution Fail: {str(e)}\"}}"

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        """
        DeepTutor-Style Orchestration Loop.
        Forces the local LLM to route intent through structured schemas,
        eliminating hallucinated paths.
        """
        orchestration_prompt = f"""
You are TutorBot, an agent-native educational companion modeled after the DeepTutor framework.
Your task is to analyze the user request and select the single most accurate capability or tool.

[CONVERSATION HISTORY]
{conversation_history}

[AVAILABLE CAPABILITIES]
- "SOLVE": Deep pedagogical breakdown of a coding or linguistic challenge.
- "QUIZ": Generate practice questions or concepts for reinforcement based on existing files.
- "RESEARCH": Explore architectural files or text references systematically.

[AVAILABLE LOW-LEVEL TOOLS]
1. search_codebase_semantics(query): Vector graph search for method logic.
2. list_tracked_file_methods(file_path): Extract mapped functions from a known path.
3. library_search(search_term): Find literary works inside the Postgres DB.
4. db_content_reader(work_id): Read text elements sequentially.

[CRITICAL INSTRUCTION]
You must respond with exactly ONE valid JSON markdown block containing your pedagogical assessment and next technical action. Do not generate raw Python scripts.

Output Shape Example:
```json
{{
    "pedagogical_intent": "Explain how the Neo4j indexing behaves before altering files.",
    "route_type": "TOOL",
    "target_name": "search_codebase_semantics",
    "target_argument": "initialize_indexes"
}}
```
[USER REQUEST]
> {user_input}
"""
        response_raw = self._call_local_llm(orchestration_prompt)
        
        # Resilient JSON Parsing Block Extraction        
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                bracket_match = re.search(r'(\{.*?\})', response_raw, re.DOTALL)
                json_str = bracket_match.group(1) if bracket_match else None

            if not json_str:
                raise ValueError("No structured JSON block could be extracted from model output.")

            action = json.loads(json_str.strip())
            
            # 1. Handle Tool Execution Branches Deterministically
            if action.get("route_type") == "TOOL":
                tool_name = action.get("target_name")
                arg = action.get("target_argument")
                
                if tool_name == "search_codebase_semantics":
                    tool_out = self.code_tools.search_semantic_code(user_query=arg)
                elif tool_name == "list_tracked_file_methods":
                    tool_out = self.code_tools.list_file_contents(file_path=arg)
                elif tool_name == "library_search":
                    tool_out = str(library_search(search_term=arg))
                elif tool_name == "db_content_reader":
                    tool_out = str(db_content_reader(work_id=int(arg)))
                else:
                    tool_out = "Target tool unrecognized."
                
                # Synergistic execution feedback loop to format the actual lesson
                return self.generate_guided_response(user_input, action["pedagogical_intent"], tool_out)
                
            # 2. Handle Direct Capability Modes
            else:
                return self.generate_guided_response(user_input, action["pedagogical_intent"], "Capability mode activated directly.")
                
        except Exception as e:
            return f"🎓 **TutorBot System Realignment**\nI encountered an actual execution exception: {str(e)}\nLet's redirect our session target manually: {response_raw}"

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, data_context: str) -> str:
        """Generates the final response ensuring it teaches the user instead of spilling raw execution dumps."""
        synthesis_prompt = f"""
You are the interactive teaching face of TutorBot. Review the factual data context retrieved and write a comprehensive, scannable, and educational response for the user.
Follow the DeepTutor method: Teach the underlying concept, map the dependencies explicitly, and guide the user through the structural layout.

Pedagogical Objective: {pedagogical_intent}
Retrieved Ground-Truth Context: {data_context}
Original Query: {user_query}

Format rules: Use clear headers, bold critical steps, and include functional code chunks inside clean blocks if necessary.
"""
        return self._call_local_llm(synthesis_prompt)

if __name__ == "__main__":
    print("\n======================================================================")
    print("🎓 DEEPTUTOR-NATIVE TUTORBOT ENGINE RUNTIME")
    print(f"Directory Anchor: {BASE_DIR} | Engine: {MODEL_NAME}")
    print("Mode: Parameter-Driven Tool Routing Layers & Multi-Stage Capability States")
    print("======================================================================\n")
    
    bot = TutorBotEngine()
    
    while True:
        try:
            user_prompt = input("🚀 UNIVERSAL-TUTOR > ")
            if user_prompt.strip().lower() in ["quit", "exit"]:
                break
            if not user_prompt.strip():
                continue
                
            history = st.fetch_chat_history(num_messages=3)
            if len(history) > 3000:
                history = "... [Older History Truncated] ...\n" + history[-3000:]
            result = bot.execute_turn(user_prompt, history)
            
            print(f"\n✨ [TutorBot Result]:\n{result}\n")
            st.save_chat_turn_to_db("user", user_prompt)
            st.save_chat_turn_to_db("ai", result)
            
        except KeyboardInterrupt:
            break
