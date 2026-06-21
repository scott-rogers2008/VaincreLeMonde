# src/agentic/tutor_engine.py
import uuid
import tutor_memories as st
from core.goal_manager import UniversalGoalManager
from core.auditor import PedagogicalAuditor
from codebase_guru.tools.agent_tools import AgentTools
from core.llm_client import LLMClient

# Import compact extracted handler components cleanly
from core.tutor_prompts import STAGE_3_SOCRATIC_TEMPLATE
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
        return self.strategy_analyzer.build_session_snapshot()

    def execute_turn(self, user_input: str, conversation_history: str) -> str:
        turn_id = str(uuid.uuid4())[:8]
        st.save_chat_turn_to_db(role="user", content=user_input)

        # 1. Delegate intent parsing and multi-pillar matching to orchestrator file
        meta = self.intent_orchestrator.process_intent_and_routing(user_input, conversation_history)
        
        primary_pillar = meta["primary_pillar"]
        search_param = meta["search_parameter"]

        try:
            # 2. Dispatch database technical lookup
            tool_out, cited_chunk = self.tool_router.dispatch(meta["action_type"], search_param, primary_pillar)
            if meta["plan_id"]:
                tool_out += "\n" + self.matrix_manager.fetch_active_plan_tree_context(meta["plan_id"])

            # Log progress scoring profiles
            target_goal_id = meta["matched_goal_id"] if meta["is_existing_goal"] else f"auto_{primary_pillar.lower()}_sync"
            if not target_goal_id: target_goal_id = f"auto_{primary_pillar.lower()}_sync"
            self.matrix_manager.log_universal_progress_turn(str(target_goal_id), 1.0, 0.5, f"DeepTutor synced: {primary_pillar}")
            
            # --- STAGE 3: SOCRATIC SYNTHESIS DELIVERY ---
            stage_3_prompt = STAGE_3_SOCRATIC_TEMPLATE.format(
                conversation_history=conversation_history,
                primary_pillar=primary_pillar, 
                associated_pillars=meta["associated_pillars"], 
                data_context=tool_out, 
                user_input=user_input
            )
            final_response, stage_3_thinking = self.llm_client.call_local_llm(stage_3_prompt)
            
            print("[🤔 DEEPTUTOR STAGE 3: SOCRATIC SYNTHESIS THINKING]")
            print(stage_3_thinking if stage_3_thinking.strip() else final_response)
            print("---------------------------------------------------\n")

            self.auditor.log_audit_trail(turn_id=turn_id, user_query=user_input, ai_response=final_response, cited_chunk_id=cited_chunk, rationale="DeepTutor loop pass.")
            st.save_chat_turn_to_db(role="assistant", content=final_response)
            
            return f"{final_response}\n\n---\n🛡️ **Pedagogical Audit Trace ID**: `audit_{turn_id}` | **Source Citation**: `{cited_chunk}`{meta['plan_log_suffix']}"

        except Exception as e:
            full_trace = f"Exception Message: {str(e)}\nException Type: {type(e).__name__}"
            agent_name, proposal = route_tutor_crash_escalation(e, search_param, user_input, full_trace)
            return f"🎓 **TutorBot System Realignment**\n\nThe system encountered an operational context block: `{str(e)}`.\nControl automatically shifted to **{agent_name}**.\n\n**Resolution Proposal:**\n\n{proposal}"

if __name__ == "__main__":
    bot = TutorBotEngine()
    print(bot.display_active_goals_session_reminder())
    while True:
        try:
            history = st.fetch_chat_history(num_messages=3)
            user_prompt = input("\n🚀 UNIVERSAL-TUTOR > ").strip()
            if user_prompt.lower() in ["quit", "exit"]: break
            if user_prompt: print(f"\n✨ [TutorBot Result]:\n{bot.execute_turn(user_prompt, history)}\n")
        except KeyboardInterrupt: break
