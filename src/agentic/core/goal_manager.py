# src/agentic/core/goal_manager.py
from falkordb import FalkorDB
from datetime import date
import json

class UniversalGoalManager:
    PILLARS = {
        "VITALITY": "Physical body, sleep, nutrition, and biological health.",
        "INNER_PEACE": "Mental health, spiritual attunement, mindset, and emotions.",
        "FINANCIAL_SECURITY": "Money, investments, financial freedom, and safety nets.",
        "RHYTHM": "Daily routines, life administration, chores, and basic organization.",
        "CRAFT": "Career, education, software development/coding, skill building, and creative output.",
        "CONNECTION": "Relationships, family, friendships, and community impact.",
        "PLAY": "Guilt-free hobbies, rest, adventures, and pure joy.",
        "SANCTUARY": "Home space, physical comfort, desk/dev setup, and surroundings."
    }

    def __init__(self):
        # Connect natively to the root container space
        self.db = FalkorDB(host='localhost', port=6379)
        self.graph = self.db.select_graph("universal_life_matrix")

    def initialize_matrix_schema(self):
        """Seeds the 8 fundamental Pillar nodes of human architecture into FalkorDB."""
        for pillar_key, desc in self.PILLARS.items():
            query = """
            MERGE (p:Pillar {id: $id})
            SET p.name = $name,
                p.description = $desc,
                p.initialized_at = $today
            """
            try:
                self.graph.query(query, {
                    "id": pillar_key,
                    "name": pillar_key.replace("_", " ").title(),
                    "desc": desc,
                    "today": date.today().isoformat()
                })
            except Exception as e:
                print(f"❌ Failed to seed Life Matrix Pillar [{pillar_key}]: {e}")
        print("✨ Universal 8-Pillar Life Matrix Schema successfully mapped in FalkorDB.")

    def add_universal_goal(self, goal_id: str, pillar: str, description: str, target_metric: str) -> str:
        """Registers a goal (e.g., coding speed, clean eating, or portfolio targets) to a Pillar."""
        clean_pillar = pillar.upper().strip()
        if clean_pillar not in self.PILLARS:
            return f"❌ Aborted: '{pillar}' is not a valid pillar inside the Universal Life Matrix."

        query = """
        MATCH (p:Pillar {id: $pillar_id})
        MERGE (g:Goal {id: $goal_id})
        SET g.description = $description,
            g.target_metric = $metric,
            g.status = 'ACTIVE',
            g.last_reviewed = $today
        MERGE (g)-[:FALLS_UNDER]->(p)
        """
        try:
            self.graph.query(query, {
                "pillar_id": clean_pillar,
                "goal_id": goal_id.strip().lower().replace(" ", "_"),
                "description": description,
                "metric": target_metric,
                "today": date.today().isoformat()
            })
            return f"✅ Goal [{goal_id}] locked down cleanly under Pillar: {clean_pillar}."
        except Exception as e:
            return f"❌ Strategic registration failed: {str(e)}"

    def log_universal_progress_turn(self, goal_id: str, success_score: float, structural_complexity: float, summary_feedback: str):
        """Logs a concrete interaction pass (like a coding exercise score or a workout log)."""
        query = """
        MATCH (g:Goal {id: $goal_id})
        CREATE (e:PerformanceRecord {
            timestamp: $today,
            score: $score,
            complexity: $complexity,
            feedback: $feedback
        })
        CREATE (g)-[:RECORDED_PERFORMANCE]->(e)
        """
        try:
            self.graph.query(query, {
                "goal_id": goal_id.strip().lower().replace(" ", "_"),
                "score": float(success_score),
                "complexity": float(structural_complexity),
                "feedback": summary_feedback,
                "today": date.today().isoformat()
            })
        except Exception as e:
            print(f"❌ Telemetry logging failed: {e}")

    def generate_matrix_health_report(self) -> dict:
        """Aggregates scores across all 8 pillars to pinpoint structural life imbalances."""
        query = """
        MATCH (p:Pillar)
        OPTIONAL MATCH (g:Goal)-[:FALLS_UNDER]->(p)
        OPTIONAL MATCH (g)-[:RECORDED_PERFORMANCE]->(e:PerformanceRecord)
        RETURN p.id AS pillar,
               avg(e.score) AS average_fulfillment,
               count(e) AS data_points
        """
        report = {"generated_at": date.today().isoformat(), "matrix": {}}
        try:
            res = self.graph.query(query)
            for row in res.result_set:
                pillar_name = row[0]
                avg_score = float(row[1]) if row[1] is not None else 0.0
                samples = int(row[2])
                report["matrix"][pillar_name] = {
                    "fulfillment_index": round(avg_score, 4),
                    "tracked_interactions": samples
                }
        except Exception as e:
            report["error"] = str(e)
        return report
