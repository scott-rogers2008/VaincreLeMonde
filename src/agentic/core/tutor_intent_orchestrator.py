# src/agentic/core/tutor_intent_orchestrator.py
from core.tutor_prompts import STAGE_1_INTENT_TEMPLATE, STAGE_2_MATRIX_TEMPLATE

class TutorIntentOrchestrator:
    def __init__(self, matrix_manager, llm_client):
        self.matrix_manager = matrix_manager
        self.llm_client = llm_client

    def process_intent_and_routing(self, user_input: str, conversation_history: str) -> dict:
        """Processes Stage 1 and Stage 2 to extract dynamic pillars, actions, and plan logs."""
        existing_goals_ctx = "None"
        try:
            g_res = self.matrix_manager.graph.query("MATCH (g:Goal) WHERE g.status = 'ACTIVE' RETURN g.id, g.description")
            if g_res.result_set:
                existing_goals_ctx = str(g_res.result_set)
        except Exception:
            pass

        # --- STAGE 1: INTENT SEPARATION ---
        stage_1_prompt = STAGE_1_INTENT_TEMPLATE.format(
            conversation_history=conversation_history,
            existing_goals_ctx=existing_goals_ctx, 
            user_input=user_input
        )
        raw_intent_out, stage_1_thinking = self.llm_client.call_local_llm(stage_1_prompt)
        
        print("\n[🤔 DEEPTUTOR STAGE 1: INTENT EXTRACTION THINKING]")
        print(stage_1_thinking if stage_1_thinking.strip() else raw_intent_out)
        print("---------------------------------------------------\n")

        intent = self.llm_client.parse_json_block(raw_intent_out)
        intent_summary = intent.get("core_intent_summary", user_input)

        # --- STAGE 2: MULTI-PILLAR ROUTING ---
        stage_2_prompt = STAGE_2_MATRIX_TEMPLATE.format(core_intent_summary=intent_summary)
        raw_matrix_out, stage_2_thinking = self.llm_client.call_local_llm(stage_2_prompt)
        
        print("[🤔 DEEPTUTOR STAGE 2: MULTI-PILLAR MATRIX THINKING]")
        print(stage_2_thinking if stage_2_thinking.strip() else raw_matrix_out)
        print("---------------------------------------------------\n")

        matrix_routing = self.llm_client.parse_json_block(raw_matrix_out)
        primary_pillar = matrix_routing.get("primary_pillar", "CRAFT")
        associated_pillars = matrix_routing.get("associated_pillars", [primary_pillar])
        
        plan_log_suffix = ""
        plan_id = None
        
        # Track structured timeline checklists
        if matrix_routing.get("is_planning_action") and matrix_routing.get("proposed_steps"):
            plan_id = matrix_routing.get("proposed_plan_id", "custom_curriculum_plan")
            plan_log_suffix = "\n\n🗺️ **New Strategy Roadmap Generated & Logged**:"
            reg_msg = self.matrix_manager.register_structured_plan(
                plan_id=plan_id,
                pillar=primary_pillar,
                description=matrix_routing.get("proposed_plan_description", "Custom Study Track"),
                steps=matrix_routing["proposed_steps"]
            )
            plan_log_suffix += f"\n {reg_msg}\n" + self.matrix_manager.fetch_active_plan_tree_context(plan_id)
        elif intent.get("requires_new_goal_registration") and intent.get("proposed_goal"):
            prop = intent["proposed_goal"]
            reg_status = self.matrix_manager.add_universal_goal(
                goal_id=prop.get("id", "custom_milestone"),
                pillar=primary_pillar,
                description=prop.get("description", "Workspace research"),
                target_metric=prop.get("target_metric", "Verification complete.")
            )
            plan_log_suffix = f"\n\n⚙️ **DeepTutor Auto-Registration**: {reg_status} (Associated Pillars: {', '.join(associated_pillars)})"

        return {
            "matched_goal_id": intent.get("matched_goal_id"),
            "is_existing_goal": intent.get("is_existing_goal"),
            "primary_pillar": primary_pillar,
            "associated_pillars": associated_pillars,
            "action_type": matrix_routing.get("technical_action", "GENERAL_MATRIX_ADVICE"),
            "search_parameter": matrix_routing.get("search_parameter", user_input),
            "plan_log_suffix": plan_log_suffix,
            "plan_id": plan_id
        }
