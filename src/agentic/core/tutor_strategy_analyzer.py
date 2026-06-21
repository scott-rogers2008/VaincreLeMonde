# src/agentic/core/tutor_strategy_analyzer.py
from core.tutor_prompts import SESSION_STRATEGY_TEMPLATE

class TutorStrategyAnalyzer:
    def __init__(self, matrix_manager, llm_client):
        self.matrix_manager = matrix_manager
        self.llm_client = llm_client

    def build_session_snapshot(self) -> str:
        """Gathers database records, lets a 9B local model generate a 1-sentence path, and builds the UI wrapper in Python."""
        # 1. Pull current active goals cleanly out of FalkorDB
        query = "MATCH (g:Goal) WHERE g.status = 'ACTIVE' RETURN g.id, g.description, g.target_metric"
        goals_list = []
        try:
            res = self.matrix_manager.graph.query(query)
            for row in res.result_set:
                goals_list.append(f" 🎯 [{str(row[0]).upper()}] - {row[1]} (Metric: {row[2]})")
        except Exception as e:
            return f"⚠️ Goal registry retrieval failed: {e}"
        
        goals_context_str = "\n".join(goals_list) if goals_list else " No active tracking goals initialized yet."
        
        # 2. Pull history context, filtering out all default automated background trackers
        history_query = """
        MATCH (g:Goal)-[:RECORDED_PERFORMANCE]->(e:PerformanceRecord)
        WHERE NOT g.id STARTS WITH 'auto_'
        RETURN g.id AS goal, e.feedback AS past_step
        ORDER BY e.timestamp DESC LIMIT 2
        """
        history_list = []
        try:
            h_res = self.matrix_manager.graph.query(history_query)
            if h_res and h_res.result_set:
                for row in h_res.result_set:
                    history_list.append(f"Last logged progress checkpoint for `{row[0]}` was: '{row[1]}'")
            else:
                history_list.append("No manual study milestones have been logged yet for this specific curriculum track.")
        except Exception:
            history_list.append("Interaction logs are currently empty.")
            
        history_context_str = "\n".join(history_list)
        
        # 3. Request ONLY a single, highly-grounded sentence proposal from your local 3080 node
        strategy_prompt = SESSION_STRATEGY_TEMPLATE.format(
            goals_context=goals_context_str,
            history_context=history_context_str
        )
        strategy_out, _ = self.llm_client.call_local_llm(strategy_prompt)
        
        # 4. Let Python reliably construct the entire layout framework structure
        snapshot_block = [
            "=========================================================================",
            "🎓 ACTIVE INSTRUCTIONAL GOALS SNAPSHOT:",
            goals_context_str,
            "-------------------------------------------------------------------------",
            "💡 COLLABORATIVE STRATEGY PROPOSAL:",
            f"   {strategy_out.strip()}",
            "========================================================================="
        ]
        return "\n".join(snapshot_block)
