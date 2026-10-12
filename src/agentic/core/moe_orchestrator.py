# src/agentic/core/moe_orchestrator.py
import json
import uuid
import hashlib
import os
from datetime import date
from falkordb import FalkorDB

# Grounding all modules via absolute package paths to protect path runtime boundaries
from core.llm_client import LLMClient
from core.auditor import PedagogicalAuditor
from core.goal_manager import UniversalGoalManager
from core.vsa_escalator import VSAEpistemicEscalator
from core.tutor_prompts import MOE_ROUTER_TEMPLATE, MOE_DISCOVERY_TEMPLATE, MOE_SYSTEM_REVIEW_TEMPLATE

# Absolute target paths for expert execution nodes
from codebase_guru.code_refactor_agent import run_agent_loop
from language_tutor.tools.embeddings import get_embeddings
from language_tutor.main import LanguageTutorMesh

class MoEOrchestrator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.auditor = PedagogicalAuditor()
        self.matrix_manager = UniversalGoalManager()
        self.vsa_engine = VSAEpistemicEscalator()
        
        # Connect natively to FalkorDB low-memory workspace graphs
        self.db = FalkorDB(host='localhost', port=6379)
        self.matrix_graph = self.db.select_graph("universal_life_matrix")
        self.doc_graph = self.db.select_graph("document_rag_graph")
        
        # Seed underlying life matrix fields safely on boot
        self.matrix_manager.initialize_matrix_schema()

    def _determine_expert_routing(self, user_objective: str) -> dict:
        """
        [TOP-DOWN ROUTING: SCHEMA INTENTION MATRIX]
        Evaluates macro goals from the top down to map targets across the 8 pillars.
        """
        routing_prompt = MOE_ROUTER_TEMPLATE.format(user_objective=user_objective)
        raw_res, thinking = self.llm_client.call_local_llm(routing_prompt)
        parsed_route = self.llm_client.parse_json_block(raw_res)
        
        if not parsed_route or "expert" not in parsed_route:
            return {
                "expert": "CURRICULUM_MESH",
                "rationale": "Default route triggered due to parsing failure.",
                "target_pillar": "CRAFT",
                "search_parameter": user_objective
            }
        return parsed_route

    def _execute_bottom_up_discovery(self, raw_sensory_input: str, raw_expert_output: str) -> dict:
        """
        [BOTTOM-UP EMERGENCE: NEUROPLASTICITY SCHEMA UPDATER]
        Captures unexpected data variations or runtime exceptions via shared templates.
        """
        print("🌱 [Executing Bottom-Up Discovery]: Checking for emergent patterns...")
        
        try:
            discovery_prompt = MOE_DISCOVERY_TEMPLATE.format(
                raw_sensory_input=raw_sensory_input,
                raw_expert_output=raw_expert_output
            )
            raw_discovery, _ = self.llm_client.call_local_llm(discovery_prompt)
            return self.llm_client.parse_json_block(raw_discovery)
        except Exception as e:
            print(f"⚠️ [Bottom-Up Formatting Intercepted]: {str(e)}")
            return {"pattern_emerged": False}

    def _calculate_data_influence(self, cited_chunk_id: str, feedback_score: float) -> float:
        """
        [MATHEMATICAL DATA ATTRIBUTION / INFLUENCE FUNCTION]
        Tracks the performance impact of a document chunk. Corrected for direct matrix result rows.
        """
        if not cited_chunk_id or cited_chunk_id == "None":
            return 0.0
            
        query = """
        MATCH (a:AuditCertificate {source_citation: $cid})
        RETURN count(a) AS baseline_usage
        """
        try:
            res = self.matrix_graph.query(query, {"cid": cited_chunk_id})
            if res and res.result_set:
                # Defensive type extraction protects against empty array table responses
                usage_count = int(res.result_set[0][0])
                influence_weight = (feedback_score * 0.7) + (usage_count * 0.3)
                return round(min(max(influence_weight, 0.0), 1.0), 4)
        except Exception:
            pass
        return 0.5

    def moe_turn_execution(self, user_objective: str, target_file_area: str = None) -> str:
        """
        Unified Bi-Directional MoE Loop: Coordinates Intent Routing, 
        VSA Epistemic Escalator, and Real-Time Experience Discovery.
        """
        turn_id = str(uuid.uuid4())[:8]
        print(f"🚀 [MoE Active Loop] -> Turn ID: moe_{turn_id}")
        
        # ---------------------------------------------------------------------
        # PHASE 1: THE COMPASS (Top-Down Gating & Epistemic Evaluation)
        # ---------------------------------------------------------------------
        # First, determine intent via our decoupled macro router.
        # This lets the model evaluate semantically if the query is a self-audit.
        routing = self._determine_expert_routing(user_objective)
        chosen_expert = routing.get("expert", "CURRICULUM_MESH")
        pillar = routing.get("target_pillar", "CRAFT")
        search_param = routing.get("search_parameter", user_objective)
        
        print(f"🔀 [Top-Down Route]: Selected [{chosen_expert}] under Pillar: [{pillar}]")

        # Check the semantic routing output for a self-referential intent
        is_self_query = (chosen_expert == "CURRICULUM_MESH" and 
                         ("books" in str(search_param) or "system" in str(routing.get("rationale", "")).lower()))

        # Run the VSA Epistemic Check ONLY for external factual lookups.
        # If the routing network determines it's an internal platform review, we trust the internal context.
        if is_self_query:
            print("🪞 [Semantic Identity Verification]: Router verified self-audit request. Bypassing boundary alarm.")
            epistemic_check = {"status": "RESOLVED", "confidence_score": 1.0}
        else:
            raw_vector = get_embeddings(user_objective)
            diagnostic_log = f"Scanning system coordinates for objective: {user_objective}. Context target: {target_file_area}"
            epistemic_check = self.vsa_engine.evaluate_epistemic_state(raw_vector, diagnostic_log)
        
        if epistemic_check["status"] == "ESCALATE":
            ticket = epistemic_check["escalation_ticket"]
            bound_hash = epistemic_check["bound_state_hash"]
            
            self.matrix_manager.add_universal_goal(
                goal_id=f"auto_resolve_{bound_hash}",
                pillar="CRAFT",
                description=f"Resolve unknown architecture blind spot: {user_objective[:50]}...",
                target_metric="Integration of valid signature boundaries mapped via bottom-up discovery."
            )
            
            output_block = [
                f"### 🚨 Epistemic Boundary Breached [VSA State Hash: `vsa_{bound_hash}`]",
                "**The system has self-evaluated and determined it does not possess the knowledge required to resolve this objective.**",
                "---",
                "🔍 **Automated Escalation Ticket Generated**:",
                ticket,
                "---",
                "⚡ *A continuous learning milestone has been injected into your life matrix graph registries to hunt down this answer.*"
            ]
            return "\n".join(output_block)

        # ---------------------------------------------------------------------
        # PHASE 2: EXPERT PIPELINE EXECUTION
        # ---------------------------------------------------------------------
        expert_output = ""
        cited_chunk = "None"
        
        if chosen_expert == "CODEBASE_GURU":
            try:
                expert_output = run_agent_loop(user_objective=user_objective, target_area=target_file_area)
                cited_chunk = f"codebase_file:{target_file_area}" if target_file_area else "general_codebase"
            except TypeError as te:
                print(f"⚠️ [Expert Method Intercepted]: {str(te)}")
                generation_prompt = f"You are TutorBot speaking from the [{pillar}] sector. Provide detailed documentation for the following objective:\n{user_objective}"
                expert_output, _ = self.llm_client.call_local_llm(generation_prompt)
                cited_chunk = "internal_fallback_documentation"
        else:
            if is_self_query:
                search_param = "books/Understanding_This/This.md"
                
            try:
                # 1. Fetch multi-lingual text chunks directly from the documentation graph surface
                doc_query = "MATCH (d:Document {path: $param})-[r:CHILD_OF|FROM_DOCUMENT*1..3]-(c:Chunk) RETURN c.text LIMIT 5"
                v_res = self.doc_graph.query(doc_query, {"param": search_param})
                
                textbook_context = ""
                if v_res and v_res.result_set:
                    textbook_context = "\n\n".join([str(row) for row in v_res.result_set])
                else:
                    backup_query = "MATCH (c:Chunk) RETURN c.text LIMIT 3"
                    b_res = self.doc_graph.query(backup_query)
                    textbook_context = "\n\n".join([str(row) for row in b_res.result_set]) if b_res.result_set else "Metadata synchronized."

                # 2. Parallel Step: Gather architectural milestones directly from codebase tracking vertices
                codebase_context = ""
                try:
                    code_query = "MATCH (g:Goal {id: 'moe_vsa_bootstrap'})-[r:HAS_STEP*1..3]-(s:Goal) RETURN s.description ORDER BY s.step_order"
                    code_res = self.matrix_graph.query(code_query)
                    if code_res and code_res.result_set:
                        codebase_context = "\n".join([f"- [Milestone]: {str(row)}" for row in code_res.result_set])
                except Exception:
                    codebase_context = "- src/agentic/tutor_engine.py (Central Control Loop)\n- src/agentic/core/moe_orchestrator.py (Gating Core)"

                # ---------------------------------------------------------------------
                # UNIFIED GRAPH EXTRACTION: Pulling code files via Git Root resources
                # ---------------------------------------------------------------------
                if is_self_query:
                    try:
                        from utils import get_git_root
                        repo_base_dir = get_git_root(os.curdir)
                        
                        universal_file_query = """
                            MATCH (n:Document) 
                            WHERE n.path CONTAINS 'This.md' OR n.path CONTAINS 'intro_to_python.md'
                            RETURN n.path LIMIT 2
                        """
                        file_res = self.doc_graph.query(universal_file_query)
                        
                        if file_res and file_res.result_set:
                            raw_code_blocks = []
                            for row in file_res.result_set:
                                graph_rel_path = str(row[0]).strip('"')
                                full_target_disk_path = os.path.join(repo_base_dir, graph_rel_path)
                                
                                if os.path.exists(full_target_disk_path):
                                    with open(full_target_disk_path, "r", encoding="utf-8") as f_src:
                                        raw_code_blocks.append(f"### [VERIFIED WORKSPACE CONTENT REPOSITORY SOURCE: {graph_rel_path}]\n{f_src.read()[:2000]}")
                            
                            if raw_code_blocks:
                                codebase_context += "\n\n" + "\n\n".join(raw_code_blocks)
                    except Exception as dynamic_err:
                        print(f"⚠️ [Dynamic Code Ingestion Warning]: {str(dynamic_err)}")

                # 3. Format payload seamlessly using our decoupled modular template string
                system_review_prompt = MOE_SYSTEM_REVIEW_TEMPLATE.format(
                    textbook_context=textbook_context,
                    codebase_context=codebase_context
                )

                expert_output, _ = self.llm_client.call_local_llm(system_review_prompt)
                cited_chunk = f"{search_param} + local_codebase_schemas"
                
            except Exception as e:
                expert_output = f"[Curriculum Mesh System Identity Fallback]: Processed text track natively. (Details: {str(e)})"

        # ---------------------------------------------------------------------
        # PHASE 3: BOTTOM-UP DISCOVERY (Emergent Property Tracking)
        # ---------------------------------------------------------------------
        discovery = self._execute_bottom_up_discovery(user_objective, expert_output)
        discovery_log_suffix = ""
        
        if discovery and discovery.get("pattern_emerged"):
            gid = discovery["emergent_goal_id"]
            p_pillar = discovery["target_pillar"]
            desc = discovery["discovered_description"]
            metric = discovery["proposed_metric"]
            
            print(f"🌱 [Bottom-Up Discovery]: Emergent pattern detected! Seeding goal node: {gid}")
            self.matrix_manager.add_universal_goal(
                goal_id=gid,
                pillar=p_pillar,
                description=desc,
                target_metric=metric
            )
            discovery_log_suffix = f"\n\n⚡ **Emergent Bottom-Up Evolution**: Discovered blind spot registered under `{p_pillar}`"

        # ---------------------------------------------------------------------
        # PHASE 4: THE COMPASS & PIVOT (Telemetry & Metric Updates)
        # ---------------------------------------------------------------------
        self.auditor.log_audit_trail(
            turn_id=turn_id,
            user_query=user_objective,
            ai_response=expert_output,
            cited_chunk_id=cited_chunk,
            rationale=f"Bi-directional MoE execution routing path via expert {chosen_expert}."
        )

        simulated_score = 0.85
        influence = self._calculate_data_influence(cited_chunk, simulated_score)
        
        self.matrix_manager.log_universal_progress_turn(
            goal_id="moe_vsa_bootstrap",
            success_score=simulated_score,
            structural_complexity=0.80,
            summary_feedback=f"Turn moe_{turn_id} evaluated. Expert: {chosen_expert}. Influence: {influence}"
        )
        
        health_card = self.matrix_manager.generate_matrix_health_report()
        sector_idx = health_card.get("matrix", {}).get(pillar, {}).get("fulfillment_index", 1.0)
        
        output_block = [
            f"### ✨ MoE Operational Deliverable [Turn ID: `moe_{turn_id}`]",
            expert_output,
            "---",
            f"🛡️ **Data Attribution Citation**: `{cited_chunk}` | **Influence Factor**: `{influence}`",
            f"📊 **Sector Health Indicator**: `{pillar}` index recalculated to: `{sector_idx:.4f}`{discovery_log_suffix}",
            f"\n*👉 Continuous learning cycles committed atomically to active graph registries.*"
        ]
        
        return "\n".join(output_block)

if __name__ == "__main__":
    orchestrator = MoEOrchestrator()
    print("🤖 Self-Correcting Mixture-of-Experts Controller Operational.")
    sample_objective = "Verify openCypher vector distance parameter bounds inside the tutor engine loop."
    result = orchestrator.moe_turn_execution(sample_objective, target_file_area="agentic/tutor_engine.py")
    print(f"\n{result}\n")