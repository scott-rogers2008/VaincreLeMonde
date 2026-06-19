# src/agentic/tutor_engine.py
import os
import json
import re
import uuid
import urllib.request
import tutor_memories as st

from core.goal_manager import UniversalGoalManager
from core.auditor import PedagogicalAuditor
from codebase_guru.tools.agent_tools import AgentTools
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b"

class TutorBotEngine:
    def __init__(self):
        self.code_tools = AgentTools()
        self.matrix_manager = UniversalGoalManager()
        self.auditor = PedagogicalAuditor()
        self.matrix_manager.initialize_matrix_schema()

    def _call_local_llm(self, prompt: str) -> str:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 8192} # Dropped temperature for strict audit consistency
        }
        try:
            req = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            return f'{{"error": "LLM Execution Fail: {str(e)}"}}'

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        """Orchestrates system turns while forcing explicit cryptographic document audits."""
        turn_id = str(uuid.uuid4())[:8]
        
        orchestration_prompt = f"""You are TutorBot, a verifiable, self-aware optimization engine.
Analyze the user request, map it to the 8-Pillar Life Matrix, and select the best technical action.

[TECHNICAL ACTIONS]
- "VECTOR_SEARCH": Read/query your uploaded self-improvement, goal setting, or multi-lingual texts.
- "LIST_METHODS": Look up structural local system python/TS code elements.
- "LIBRARY_SEARCH": Read legacy SQL catalog entries.
- "GENERAL_MATRIX_ADVICE": Handle generic life planning.

[CRITICAL INSTRUCTION FOR SELF-AWARE INTEGRITY]
You must cite the exact concept parameter or chunk name you are basing your pedagogical approach on.
Return exactly ONE JSON block:
```json
{{
  "targeted_pillar": "CRAFT",
  "pedagogical_intent": "Apply systematic Socratic reasoning to optimize software development paths.",
  "action_type": "VECTOR_SEARCH",
  "search_parameter": "target concept text",
  "audit_teaching_rationale": "Applying the active spaced-repetition core guidelines from your learning text documents."
}}
```
> {user_input}
"""
        response_raw = self._call_llm_or_fallback_json(orchestration_prompt)
        try:
            action = self._parse_json_block(response_raw)
            pillar = action.get("targeted_pillar", "CRAFT")
            pedagogical_intent = action.get("pedagogical_intent", "Matrix alignment execution.")
            action_type = action.get("action_type")
            param = action.get("search_parameter")
            rationale = action.get("audit_teaching_rationale", "Standard educational deployment pass.")
            
            tool_out = ""
            cited_chunk = "None"

            if action_type == "VECTOR_SEARCH":
                active_graph_space = self.code_tools.db.select_graph("document_rag_graph")
                query = """
                CALL db.idx.vector.queryNodes('Chunk', 'embedding', 1, vecf32($vector)) YIELD node, score
                RETURN node.chunk_id AS identity, node.text AS text, score
                """
                vector_data = get_multilingual_embedding(param)
                if vector_data and isinstance(vector_data, list):
                    sanitized_vector = [float(x) for x in vector_data]
                    res = active_graph_space.query(query, {"vector": sanitized_vector})
                    
                    if res.result_set:
                        row = res.result_set[0]
                        identity_val = row[0]
                        text_val = row[1]
                        score_val = float(row[2])
                        
                        cited_chunk = str(identity_val) if identity_val is not None else "Doc-Chunk"
                        tool_out = f"--- Verified Source Document Match: {cited_chunk} (Score: {score_val:.4f}) ---\n{str(text_val)}"
                    else:
                        tool_out = "Search completed, but no explicit matching document nodes were found."
                else:
                    tool_out = "Failed to calculate a valid document lookup vector."
           
            elif action_type == "LIST_METHODS":
                tool_out = self.code_tools.list_file_contents(param)
            elif action_type == "LIBRARY_SEARCH":
                tool_out = str(library_search(search_term=param))
            elif action_type == "GENERAL_MATRIX_ADVICE":
                tool_out = f"Navigating guidelines inside the [{pillar}] sector entries."

            # Commit interaction metrics
            self.matrix_manager.log_universal_progress_turn(
                goal_id=f"auto_{pillar.lower()}_sync", success_score=1.0,
                structural_complexity=0.5, summary_feedback=pedagogical_intent
            )

            # Generate final response context
            final_response = self.generate_guided_response(user_input, pedagogical_intent, pillar, tool_out)

            # 🔒 FORCE COMPLIANCE VERIFICATION: Log immutable audit track entry
            self.auditor.log_audit_trail(
                turn_id=turn_id, user_query=user_input, ai_response=final_response,
                cited_chunk_id=cited_chunk, rationale=rationale
            )

            # Append metadata trace cleanly to help the user check the compliance logs instantly
            return f"{final_response}\n\n---\n🛡️ **Pedagogical Audit Trace ID**: `audit_{turn_id}` | **Source Citation**: `{cited_chunk}`"

        except Exception as e:
            error_msg = str(e)
            
            # 1. COMPILE HIGH-DENSITY VERBOSE INSPECTION METRICS
            diagnostic_payload = [
                f"Exception Message: {error_msg}",
                f"Exception Type   : {type(e).__name__}"
            ]
            
            if 'res' in locals():
                diagnostic_payload.append(f"Result Set Type  : {type(res).__name__}")
                if hasattr(res, 'result_set'):
                    diagnostic_payload.append(f"Raw Result Set   : {res.result_set}")
                    if len(res.result_set) > 0:
                        diagnostic_payload.append(f"First Row Type   : {type(res.result_set[0]).__name__}")
                        diagnostic_payload.append(f"First Row Items  : {res.result_set[0]}")
            
            if 'action' in locals():
                diagnostic_payload.append(f"Parsed Action JSON: {action}")
                
            full_verbose_trace = "\n".join(diagnostic_payload)
            
            # Verbatim mirror to terminal stream for instant visibility
            print("\n================== 🚨 TUTORBOT RUNTIME EXCEPTION TRACE ==================")
            print(full_verbose_trace)
            print("=========================================================================\n")

            # 2. TRIGGER DUAL ESCALATION Agent CHANNELS PASSING THE VERBOSE STREAM
            if "code_tools" in error_msg or "list_file_contents" in error_msg or "result_set" in error_msg or "codebase" in user_input.lower():
                print("⚡ Triggering Code Refactor Agent escalation chain with verbose trace...")
                from codebase_guru.code_refactor_agent import run_agent_loop
                
                # Pass the exact runtime structural anomalies down to the refactor engine loop
                agent_proposal = run_agent_loop(
                    user_objective=(
                        f"Fix a runtime variable unpacking/attribute mismatch in tutor_engine.py. "
                        f"Review the full raw trace details here:\n\n{full_verbose_trace}\n\n"
                        f"Modify the target block to unpack FalkorDB results using safe scalar property indices."
                    ),
                    target_area="agentic/tutor_engine.py"
                )
                agent_name = "Code Refactor Agent"
            else:
                print("⚡ Triggering Document Concept Agent escalation chain...")
                from document_concept_agent import DocumentConceptAgent
                doc_agent = DocumentConceptAgent()
                agent_proposal = doc_agent.execute_document_recovery_loop(
                    failed_task=f"Resolve database syntax or multi-lingual search issue for request: '{user_input}'",
                    error_trace=full_verbose_trace
                )
                agent_name = "Document Concept Agent"
                
            return f"🎓 **TutorBot System Realignment**\n\n" \
                   f"The system encountered a structural runtime crash: `{error_msg}`.\n" \
                   f"Control was automatically handed over to the **{agent_name}** to review and fix the workspace state.\n\n" \
                   f"**Resolution Proposal:**\n\n{agent_proposal}"

    def _call_llm_or_fallback_json(self, prompt: str) -> str:
        return self._call_local_llm(prompt)

    def _parse_json_block(self, text: str) -> dict:
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        json_str = json_match.group(1) if json_match else text
        if not json_match:
            bracket_match = re.search(r'(\{.*?\})', text, re.DOTALL)
            json_str = bracket_match.group(1) if bracket_match else text
        return json.loads(json_str.strip().replace("\n", " "))

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, pillar: str, data_context: str) -> str:
        synthesis_prompt = f"""You are TutorBot, speaking from the [{pillar}] sector of the Life Matrix.
You must construct your reply strictly using the verified document facts provided in the Context Base.

Pedagogical Target: {pedagogical_intent}
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