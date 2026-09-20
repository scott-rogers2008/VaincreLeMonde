# src/agentic/tutor_engine.py
import uuid
import tutor_memories as st
from core.goal_manager import UniversalGoalManager
from core.auditor import PedagogicalAuditor
from codebase_guru.tools.agent_tools import AgentTools
from core.llm_client import LLMClient

# Import compact extracted handler components cleanly
from core.tutor_prompts import (
    QUIZ_GENERATION_TEMPLATE,
    QUIZ_GRADING_TEMPLATE,
    SESSION_STRATEGY_TEMPLATE
)
from core.tutor_tool_router import TutorToolRouter
from core.tutor_escalator import route_tutor_crash_escalation
from core.tutor_strategy_analyzer import TutorStrategyAnalyzer
from core.tutor_intent_orchestrator import TutorIntentOrchestrator

class TutorBotEngine:
    def __init__(self):
        self.code_tools = AgentTools()
        self.matrix_manager = UniversalGoalManager()
        self.auditor = PedagogicalAuditor()
        self.llm_client = LLMClient()
        self.tool_router = TutorToolRouter(self.code_tools)
        
        # Bind separated modules
        self.strategy_analyzer = TutorStrategyAnalyzer(self.matrix_manager, self.llm_client)
        self.intent_orchestrator = TutorIntentOrchestrator(self.matrix_manager, self.llm_client)
        self.matrix_manager.initialize_matrix_schema()

    def display_active_goals_session_reminder(self) -> str:
        """Queries current goals and performance records to suggest what to review next."""
        session_snapshot = self.strategy_analyzer.build_session_snapshot()
        report = self.matrix_manager.generate_matrix_health_report()
        matrix_data = report.get("matrix", {})
        
        lines = [
            session_snapshot,
            "🎓 DEEPTUTOR SPACED-REPETITION INTERACTIVE DASHBOARD"
            ]
        
        for pillar, metrics in matrix_data.items():
            idx = metrics["fulfillment_index"]
            samples = metrics["tracked_interactions"]
            status_marker = "🚨 Needs Review" if idx < 0.7 else "✅ Retained"
            if samples == 0: status_marker = "⏳ Unchecked"
            lines.append(f" 📊 Sector: {pillar:<20} | Retention Index: {idx:.2f} ({samples} Reviews) [{status_marker}]")
            
        lines.append("-------------------------------------------------------------------------")
        lines.append("💡 TYPE A COMMAND TO START:")
        lines.append("   'quiz <goal_id>'     -> Start a grounded review session over a target module.")
        lines.append("   'status'             -> Regenerate this performance reporting card.")
        lines.append("=========================================================================")
        return "\n".join(lines)

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        turn_id = str(uuid.uuid4())[:8]
        clean_input = user_input.strip()
        st.save_chat_turn_to_db(role="user", content=clean_input)

        # ---------------------------------------------------------------------
        # PATTERN A: EVALUATE ACTIVE INTERACTIVE QUIZ ANSWERS
        # ---------------------------------------------------------------------
        if self.active_quiz_cache.get("is_active"):
            cached = self.active_quiz_cache
            print(f"🧠 [DeepTutor]: Grading your answer against source documentation facts...")
            
            grading_prompt = QUIZ_GRADING_TEMPLATE.format(
                data_context=cached["context"],
                quiz_question=cached["question"],
                student_answer=clean_input
            )
            raw_grade_out, reasoning = self.llm_client.call_local_llm(grading_prompt)
            grade_data = self.llm_client.parse_json_block(raw_grade_out)
            
            score = float(grade_data.get("score", 0.5))
            complexity = float(grade_data.get("complexity", 0.5))
            rationale = grade_data.get("rationale", "Completed evaluation loop pass.")
            
            # Persist performance scores straight to your FalkorDB universal_life_matrix
            self.matrix_manager.log_universal_progress_turn(
                goal_id=cached["goal_id"],
                success_score=score,
                structural_complexity=complexity,
                summary_feedback=f"Question: {cached['question'][:60]}... | Grade: {score:.2f}"
            )
            
            # Commits cryptographically signed certificate to prove data grounding rules
            self.auditor.log_audit_trail(
                turn_id=turn_id,
                user_query=cached["question"],
                ai_response=raw_grade_out,
                cited_chunk_id=cached["chunk_id"],
                rationale=rationale
            )
            
            # Wipe session state to close quiz sequence
            self.active_quiz_cache = {}
            
            response = f"### 📊 Quiz Evaluation Report\n\n**Score:** `{score * 100:.1f}%`\n**Evaluation:** {rationale}\n\n---\n*Spaced repetition telemetry written to system matrices. Type 'status' to review metrics.*"
            st.save_chat_turn_to_db(role="assistant", content=response)
            return response

        # ---------------------------------------------------------------------
        # PATTERN B: PARSE SPECIAL COMMAND INTERCEPTS
        # ---------------------------------------------------------------------
        if clean_input.lower() == "status":
            return self.display_active_goals_session_reminder()
            
        if clean_input.lower().startswith("quiz "):
            target_goal_id = clean_input[5:].strip().lower().replace(" ", "_")
            print(f"📡 Harvesting grounding text context layers for: '{target_goal_id}'...")
            
            try:
                # Dispatch database lookup via cross-graph tool routing mechanics
                tool_out, cited_chunk = self.tool_router.dispatch("VECTOR_SEARCH", target_goal_id, "CRAFT")
                
                # Fetch descriptive markers from the target matrix goal node
                goal_desc = "General core documentation review track."
                g_query = "MATCH (g:Goal {id: \$gid}) RETURN g.description"
                g_res = self.matrix_manager.graph.query(g_query, {"gid": target_goal_id})
                if g_res.result_set:
                    goal_desc = str(g_res.result_set[0][0])
                
                quiz_prompt = QUIZ_GENERATION_TEMPLATE.format(
                    goal_id=target_goal_id,
                    goal_desc=goal_desc,
                    data_context=tool_out
                )
                
                raw_quiz_question, thinking = self.llm_client.call_local_llm(quiz_prompt)
                
                # Cache active session indicators to intercept user response on the next turn
                self.active_quiz_cache = {
                    "is_active": True,
                    "goal_id": target_goal_id,
                    "question": raw_quiz_question,
                    "context": tool_out,
                    "chunk_id": cited_chunk
                }
                
                st.save_chat_turn_to_db(role="assistant", content=raw_quiz_question)
                return f"{raw_quiz_question}\n\n---\n🛡️ **Pedagogical Audit Trace ID**: `audit_{turn_id}` | **Source Citation**: `{cited_chunk}`\n*👉 Please type your complete conceptual answer below to be graded.*"
                
            except Exception as e:
                return f"❌ **Failed to launch quiz sequence**: `{str(e)}`. Make sure you have initialized the target goal key inside your matrix graph parameters."

        # ---------------------------------------------------------------------
        # PATTERN C: STANDARD GROUNDED CHAT CONVERSATION
        # ---------------------------------------------------------------------
        try:
            tool_out, cited_chunk = self.tool_router.dispatch("VECTOR_SEARCH", clean_input, "CRAFT")
            synthesis_prompt = f"You are TutorBot. Provide a concise explanation grounded strictly in this context:\n\n{tool_out}\n\nQuery: {clean_input}"
            final_response, _ = self.llm_client.call_local_llm(synthesis_prompt)
            
            self.auditor.log_audit_trail(turn_id=turn_id, user_query=clean_input, ai_response=final_response, cited_chunk_id=cited_chunk, rationale="Standard conversation tracking.")
            st.save_chat_turn_to_db(role="assistant", content=final_response)
            return f"{final_response}\n\n---\n🛡️ **Source Citation**: `{cited_chunk}`"
        except Exception:
            # Simple conversational fallback if zero context tokens hit
            fallback_prompt = f"You are an AI assistant. Answer this query directly and concisely: {clean_input}"
            res, _ = self.llm_client.call_local_llm(fallback_prompt)
            return res

if __name__ == "__main__":
    bot = TutorBotEngine()
    print(bot.display_active_goals_session_reminder())
    while True:
        try:
            history = st.fetch_chat_history(num_messages=3)
            user_prompt = input("\n🚀 UNIVERSAL-RECALL-TUTOR > ").strip()
            if user_prompt.lower() in ["quit", "exit"]: break
            if user_prompt: print(f"\n✨ [TutorBot Result]:\n{bot.execute_turn(user_prompt, history)}\n")
        except KeyboardInterrupt: break
    print("👋 Goodbye!")