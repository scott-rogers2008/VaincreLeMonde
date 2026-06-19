# src/agentic/tutor_engine.py
import os
import json
import re
import urllib.request
from utils import get_git_root
import tutor_memories as st

from codebase_guru.tools.agent_tools import AgentTools
from language_tutor.tools.database_tools import db_content_reader
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

BASE_DIR = os.path.abspath(get_git_root(os.curdir))
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b"

class TutorBotEngine:
    def __init__(self):
        self.code_tools = AgentTools()

    def _call_local_llm(self, prompt: str) -> str:
        payload = {
            "model": MODEL_NAME, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192}
        }
        try:
            req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            return f'{{"error": "LLM Execution Fail: {str(e)}"}}'

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        orchestration_prompt = f"""
        You are TutorBot, operating over an active FalkorDB instance.
        Determine the next technical action based on the user request.

        [GRAPH SCHEMA ENVIRONMENT]
        - Code Base Vector Area: 768D English model tokens via 'codebase_guru'.
        - Document/Lexicon Area: 1024D Multi-lingual model tokens via 'document_rag_graph'.

        [AVAILABLE ACTIONS]
        1. "VECTOR_SEARCH": Used to pull multi-lingual document text, terms, or meanings.
        2. "LIST_METHODS": Used to map folders or look up local structural code functions.
        3. "LIBRARY_SEARCH": Used to inspect the SQL literary database storage rows.

        Return exactly ONE JSON block:
        ```json
        {{
          "pedagogical_intent": "Brief operational metric goals target description.",
          "action_type": "VECTOR_SEARCH",
          "target_label": "Sense",
          "search_parameter": "target conceptual string"
        }}
        ```
        > {user_input}
        """
        response_raw = self._call_local_llm(orchestration_prompt)
        
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_raw, re.DOTALL)
            json_str = json_match.group(1) if json_match else response_raw
            if not json_match:
                bracket_match = re.search(r'(\{.*?\})', response_raw, re.DOTALL)
                json_str = bracket_match.group(1) if bracket_match else response_raw
            
            action = json.loads(json_str.strip().replace("\n", " "))
            action_type = action.get("action_type")
            param = action.get("search_parameter")
            tool_out = ""

            if action_type == "VECTOR_SEARCH":
                requested_label = str(action.get("target_label", "Chunk")).strip()
                limit_val = int(action.get("limit", 3))
                
                # 1. FORCE SCHEMA COMPLIANCE
                # Map any abstract query variants strictly to our markdown chunk structures
                label = "Chunk"

                # 2. RESOLVE GRAPH INSTANCE BOUNDARY
                active_graph_space = self.code_tools.db.select_graph("document_rag_graph")
                space_debug_name = "document_rag_graph (1024D Multi-lingual)"

                # 4. OFFICIAL RETRIEVAL PASSTHROUGH SIGNATURE
                query = f"""
                CALL db.idx.vector.queryNodes('{label}', 'embedding', {limit_val}, vecf32($vector)) 
                YIELD node, score 
                RETURN node.chunk_id AS identity, node.text AS text, score
                """
                
                # Extract 1024D multi-lingual arrays from your active BGE model
                vector_data = get_multilingual_embedding(param)
                
                # 📡 STACK VERIFICATION DIAGNOSTIC DISPLAY
                print("\n=================== 📡 FALKORDB NETWORK DIAGNOSTIC ===================")
                print(f"Target Graph Space  : {space_debug_name}")
                print(f"Falkor Index Name   : {label}")
                print(f"Compiled Cypher     : {query.strip()}")
                print(f"Vector Dimensions   : {len(vector_data) if isinstance(vector_data, list) else 'Invalid'}")
                print("======================================================================\n")

                if vector_data and isinstance(vector_data, list):
                    sanitized_vector = [float(x) for x in vector_data]
                    res = active_graph_space.query(query, {"vector": sanitized_vector})
                    
                    blocks = []
                    for identity_val, text_val, score_val in res.result_set:
                        node_id = identity_val if identity_val is not None else "Doc-Chunk"
                        blocks.append(f"--- Doc Chunk ID: {node_id} (Score: {score_val:.4f}) ---\nText Content: {str(text_val)}")
                        
                    tool_out = "\n\n".join(blocks) if blocks else f"Index search executed successfully, but no matching markdown text was found."
                else:
                    tool_out = "Error extracting valid multi-lingual document vector array."

            elif action_type == "LIST_METHODS":
                tool_out = self.code_tools.list_file_contents(param)

            elif action_type == "LIBRARY_SEARCH":
                tool_out = str(library_search(search_term=param))

            return self.generate_guided_response(user_input, action["pedagogical_intent"], tool_out)

        except Exception as e:
            error_msg = str(e)
            print(f"\n🚨 [TutorBotEngine: Runtime Exception Trapped]: {error_msg}")
            
            # 🧠 DUAL ESCALATION ROUTING LAYER
            # Route to Codebase Refactor Agent if the failure point involves python, modules, or code file paths
            if "code_tools" in error_msg or "list_file_contents" in error_msg or "codebase" in user_input.lower():
                print("⚡ Triggering Code Refactor Agent escalation chain...")
                from codebase_guru.code_refactor_agent import run_agent_loop
                agent_proposal = run_agent_loop(
                    user_objective=f"Fix runtime tool failure for request: '{user_input}'. Trace: {error_msg}",
                    target_area="agentic/tutor_engine.py"
                )
                agent_name = "Code Refactor Agent"
            else:
                # Route to Document Concept Agent for data structure, vector arrays, or document graph issues
                print("⚡ Triggering Document Concept Agent escalation chain...")
                from document_concept_agent import DocumentConceptAgent
                doc_agent = DocumentConceptAgent()
                agent_proposal = doc_agent.execute_document_recovery_loop(
                    failed_task=f"Resolve database syntax or multi-lingual search issue for request: '{user_input}'",
                    error_trace=error_msg
                )
                agent_name = "Document Concept Agent"
                
            return f"🎓 **TutorBot System Realignment**\n\n" \
                   f"The system encountered a structural runtime crash: `{error_msg}`.\n" \
                   f"Control was automatically handed over to the **{agent_name}** to review and fix the workspace state.\n\n" \
                   f"**Resolution Proposal:**\n\n{agent_proposal}"

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, data_context: str) -> str:
        synthesis_prompt = f"""
        You are the educational face of TutorBot. Complete the following target parameters:
        Objective: {pedagogical_intent}
        Context Base: {data_context}
        Query: {user_query}
        """
        return self._call_local_llm(synthesis_prompt)

if __name__ == "__main__":
    bot = TutorBotEngine()
    while True:
        try:
            user_prompt = input("🚀 UNIVERSAL-TUTOR > ").strip()
            if user_prompt.lower() in ["quit", "exit"]:
                break
            if not user_prompt:
                continue
            history = st.fetch_chat_history(num_messages=3)
            print(f"\n✨ [TutorBot Result]:\n{bot.execute_turn(user_prompt, history)}\n")
        except KeyboardInterrupt:
            break
    print("👋 Exiting TutorBot. Goodbye!")