# src/agentic/tutor_engine.py
import os
import json
import re
import urllib.request
from utils import get_git_root
import tutor_memories as st

# Direct, frameworkless backend driver imports
from codebase_guru.tools.agent_tools import AgentTools
from language_tutor.tools.database_tools import db_content_reader
from language_tutor.tools.library_tools import library_search

BASE_DIR = os.path.abspath(get_git_root(os.curdir))
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b" # Parameter-scale champion optimized for local intent routing

class TutorBotEngine:
    def __init__(self):
        # Bind cleanly to our newly unified FalkorDB tool belt
        self.code_tools = AgentTools()

    def _call_local_llm(self, prompt: str) -> str:
        """Low-level robust local LLM execution with strict context ceiling protection."""
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192
            }
        }
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            return f'{{"error": "LLM Execution Fail: {str(e)}"}}'

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        """
        DeepTutor-Style Orchestration Loop. Forces the local LLM to route intent 
        through structured JSON parameters, eliminating hallucinated library calls.
        """
        orchestration_prompt = f"""
        You are TutorBot, an expert educational graph architect operating over a FalkorDB runtime instance.
        Analyze the user input and determine the next technical action.

        [GRAPH SCHEMA DEFINITION]
        Our system tracks vocabulary and codebase structures using three explicit node labels:
        1. (:File {{path, hash}}) -> Mapped code documents.
        2. (:Method {{name, body_hash}}) -> Class components or functions.
        3. (:Chunk {{chunk_id, text}}) -> Splitted code fragments or story text segments.

        Valid Relationship Vectors:
        - (:File)-[:CONTAINS]->(:Method)
        - (:Method)-[:HAS_CHUNK]->(:Chunk)
        - (:Chunk)-[:RELATED_TO]->(:Lexeme)

        [AVAILABLE TECHNICAL ACTIONS]
        1. "VECTOR_SEARCH": Use this if the user is looking for code concepts or textual themes.
        2. "LIST_METHODS": Use this if the user provides a specific folder path and wants a structural map.
        3. "LIBRARY_SEARCH": Use this if the user wants to search for stories or authors in the library database.

        [CRITICAL OUTPUT CONSTRAINT]
        You must respond with exactly ONE valid JSON block matching this structural shape. 
        Do not write raw openCypher query text strings. Do not use conversational chatter.

        Output Shape Specification:
        ```json
        {{
            "pedagogical_intent": "Locate the vector chunk containing the system path logic.",
            "action_type": "VECTOR_SEARCH",
            "target_label": "Chunk",
            "search_parameter": "universal root path calculations"
        }}
        ```

        [USER REQUEST]
        > {user_input}
        """
        response_raw = self._call_local_llm(orchestration_prompt)

        # Resilient JSON Parsing Block Extraction
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_raw, re.DOTALL)
            json_str = json_match.group(1) if json_match else response_raw
            if not json_match:
                bracket_match = re.search(r'(\{.*?\})', response_raw, re.DOTALL)
                json_str = bracket_match.group(1) if bracket_match else response_raw

            action = json.loads(json_str.strip().replace("\n", " "))
            tool_out = ""
            action_type = action.get("action_type")
            param = action.get("search_parameter")

            if action_type == "VECTOR_SEARCH":
                label = action.get("target_label", "Sense") # Target the Sense label for vector lookups
                
                # CORRECT SYNTAX: Use FalkorDB's native VECTOR_SEARCH function in the WHERE clause
                query = f"""
                    MATCH (n:{label})
                    WHERE VECTOR_SEARCH(n.embedding, vecf32($vector), $limit)
                    MATCH (l:Lexeme)-[:HAS_SENSE]->(n)
                    RETURN l.text AS identity, n.definition AS text, 1.0 AS score
                """
                vector_data = self.code_tools.embedder.get_embedding(param)
                if vector_data:
                    # Pass parameters to the query
                    res = self.code_tools.graph.query(query, {"vector": vector_data, "limit": 3})
                    blocks = []
                    for identity_val, text_val, score_val in res.result_set:
                        blocks.append(f"--- Word: {identity_val} ---\nDefinition: {str(text_val)}")
                    tool_out = "\n\n".join(blocks) if blocks else "No matching definitions located."
                else:
                    tool_out = "Error generating vector for query step."

            elif action_type == "LIST_METHODS":
                # PROPERTY MAPPING FIX: Handle prompt variance by grabbing param as a fallback
                file_path = action.get("file_path", param)
                tool_out = self.code_tools.list_file_contents(file_path)

            elif action_type == "LIBRARY_SEARCH":
                tool_out = str(library_search(search_term=param))
                
            else:
                tool_out = "Direct pedagogical capability state activated."

            return self.generate_guided_response(user_input, action["pedagogical_intent"], tool_out)

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

        Format rules: Use clear headers, bold critical steps, and include functional code chunks inside clean markdown blocks if necessary.
        """
        return self._call_local_llm(synthesis_prompt)

if __name__ == "__main__":
    print("\n======================================================================")
    print("🎓 DEEPTUTOR-NATIVE TUTORBOT ENGINE RUNTIME (FALKORDB OPTIMIZED)")
    print(f"Directory Anchor: {BASE_DIR} | Engine Core: {MODEL_NAME}")
    print("======================================================================\n")
    
    bot = TutorBotEngine()
    while True:
        try:
            user_prompt = input("🚀 UNIVERSAL-TUTOR > ").strip()
            if user_prompt.lower() in ["quit", "exit"]:
                break
            if not user_prompt:
                continue

            # Load past conversation context chunks from long-term memory registries
            history = st.fetch_chat_history(num_messages=3)
            if len(history) > 3000:
                history = "... [Older History Truncated] ...\n" + history[-3000:]

            result = bot.execute_turn(user_prompt, history)
            print(f"\n✨ [TutorBot Result]:\n{result}\n")

            # Persist chat cycles cleanly to PostgreSQL
            st.save_chat_turn_to_db("user", user_prompt)
            st.save_chat_turn_to_db("ai", result)

        except KeyboardInterrupt:
            break
