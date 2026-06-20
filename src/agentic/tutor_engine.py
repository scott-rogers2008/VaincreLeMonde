# src/agentic/tutor_engine.py
import os
import json
import uuid
import tutor_memories as st
from core.goal_manager import UniversalGoalManager
from core.auditor import PedagogicalAuditor
from codebase_guru.tools.agent_tools import AgentTools
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

# Import the newly extracted core module
from core.llm_client import LLMClient

class TutorBotEngine:
    def __init__(self):
        self.code_tools = AgentTools()
        self.matrix_manager = UniversalGoalManager()
        self.auditor = PedagogicalAuditor()
        
        # Initialize the client module
        self.llm_client = LLMClient()
        self.matrix_manager.initialize_matrix_schema()

    # --- BACKWARD COMPATIBILITY LAYERS ---
    def _call_local_llm(self, prompt: str) -> str:
        return self.llm_client.call_local_llm(prompt)

    def _call_llm_or_fallback_json(self, prompt: str) -> str:
        return self.llm_client.call_local_llm(prompt)

    def _parse_json_block(self, text: str) -> dict:
        return self.llm_client.parse_json_block(text)

    def generate_guided_response(self, user_query: str, pedagogical_intent: str, pillar: str, data_context: str) -> str:
        return self.llm_client.generate_guided_response(user_query, pedagogical_intent, pillar, data_context)
    # -------------------------------------

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        """
        Orchestration State Machine. Decides which sub-agent tool system to query
        and maps interaction telemetry against the 8-Pillar Universal Life Matrix.
        """
        turn_id = str(uuid.uuid4())[:8]
        
        orchestration_prompt = f"""You are TutorBot, a verifiable, self-aware optimization engine.
Analyze the user request, map it to the 8-Pillar Life Matrix, and select the best technical action.

[THE 8 PILLARS]
- VITALITY (Physical health, biology, sleep)
- INNER_PEACE (Mindset, meditative focus, emotions)
- FINANCIAL_SECURITY (Wealth assets, safety nets)
- RHYTHM (Daily routines, admin tasks, organization)
- CRAFT (Coding, refactoring, languages, skill building, creative output)
- CONNECTION (Relationships, family, communication impact)
- PLAY (Hobbies, active recreation, joy)
- SANCTUARY (Physical home space, environment, dev desk)

[GRAPH SCHEMA ENVIRONMENT]
- Code Base Vector Area: 768D English model tokens via 'codebase_guru'.
- Document/Lexicon Area: 1024D Multi-lingual model tokens via 'document_rag_graph'.

[AVAILABLE TECHNICAL ACTIONS]
1. "VECTOR_SEARCH": Used to pull multi-lingual document text, terms, or meanings.
2. "LIST_METHODS": Used to map folders or look up local structural code functions.
3. "LIBRARY_SEARCH": Used to inspect the SQL literary database storage rows.
4. "GENERAL_MATRIX_ADVICE": Used for life matrix goals, routines, or general development.

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
                CALL db.idx.vector.queryNodes('Chunk', 'embedding', 1, vecf32($param_vector)) YIELD node, score
                RETURN node.chunk_id AS identity, node.text AS text, score
                """
                vector_data = get_multilingual_embedding(param)
                if vector_data and isinstance(vector_data, list):
                    sanitized_vector = [float(x) for x in vector_data]
                    res = active_graph_space.query(query, {"param_vector": sanitized_vector})
                    
                    if res and hasattr(res, 'records') and res.records:
                        row = res.records[0]
                        try:
                            identity_val = row[0]
                            text_val = row[1]
                            score_val = float(row[2])
                        except Exception:
                            identity_val = "Doc-Chunk"
                            text_val = str(row)
                            score_val = 0.0
                                
                        cited_chunk = str(identity_val) if identity_val is not None else "Doc-Chunk"
                        tool_out = f"--- Verified Source Document Match: {cited_chunk} (Score: {score_val:.4f}) ---\n{str(text_val)}"
                    else:
                        # CRITICAL ESCALATION FIX: Force a custom exception if search yields empty data models
                        # This bridges the gap between database structural successes and semantic information deficits!
                        raise LookupError(f"Missing Essential Context: Vector index lookup for '{param}' returned 0 records.")
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

            # FORCE COMPLIANCE VERIFICATION: Log immutable audit track entry
            self.auditor.log_audit_trail(
                turn_id=turn_id, user_query=user_input, ai_response=final_response,
                cited_chunk_id=cited_chunk, rationale=rationale
            )

            return f"{final_response}\n\n---\n🛡️ **Pedagogical Audit Trace ID**: `audit_{turn_id}` | **Source Citation**: `{cited_chunk}`"

        except Exception as e:
            error_msg = str(e)
            
            # COMPILE HIGH-DENSITY VERBOSE INSPECTION METRICS
            diagnostic_payload = [
                f"Exception Message: {error_msg}",
                f"Exception Type   : {type(e).__name__}"
            ]
            if 'action' in locals():
                diagnostic_payload.append(f"Parsed Action JSON: {action}")
            full_verbose_trace = "\n".join(diagnostic_payload)
            
            print("\n================== 🚨 TUTORBOT RUNTIME EXCEPTION TRACE ==================")
            print(full_verbose_trace)
            print("=========================================================================\n")

            # INTERCEPT KNOWLEDGE DRIFT OR PARAMETER ERRORS FOR RESOLUTION GENERATION
            # If the error is a LookupError (missing documents), route to Document Concept Agent
            if isinstance(e, LookupError) or "missing essential context" in error_msg.lower():
                print("⚡ Triggering Document Concept Agent escalation chain for context recovery...")
                from document_concept_agent import DocumentConceptAgent
                doc_agent = DocumentConceptAgent()
                
                # Pass the exact semantic parameters directly to the recovery loop meta-prompter
                agent_proposal = doc_agent.execute_document_recovery_loop(
                    failed_task=f"Resolve empty vector-search bounds for parameter: '{param if 'param' in locals() else user_input}'",
                    error_trace=full_verbose_trace
                )
                agent_name = "Document Concept Agent"
            else:
                # If it's a code-level crash, route to Code Refactor Agent
                print("⚡ Triggering Code Refactor Agent escalation chain with targeted file focus...")
                from codebase_guru.code_refactor_agent import run_agent_loop
                agent_proposal = run_agent_loop(
                    user_objective=(
                        f"Fix a code exception inside tutor_engine.py. Trace:\n\n{full_verbose_trace}\n\n"
                        f"Task: Review variable usage on target line scopes to fix attribute parsing bugs."
                    ),
                    target_area="agentic/tutor_engine.py"
                )
                agent_name = "Code Refactor Agent"
                
            return f"🎓 **TutorBot System Realignment**\n\n" \
                   f"The system encountered an operational context block: `{error_msg}`.\n" \
                   f"Control was automatically handed over to the **{agent_name}** to review and fix the workspace state.\n\n" \
                   f"**Resolution Proposal:**\n\n{agent_proposal}"

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