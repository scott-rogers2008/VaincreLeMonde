# src/agentic/document_concept_agent.py
import os
import json
import re
import urllib.request
from datetime import date
from falkordb import FalkorDB
from .utils import get_git_root
from .language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

MODEL_NAME = "deepseek-r1:14b"
OLLAMA_URL = "http://localhost:11434/api/generate"

class DocumentConceptAgent:
    def __init__(self):
        self.db = FalkorDB(host='localhost', port=6379)
        self.graph = self.db.select_graph("document_rag_graph")

    def _call_ollama_reasoning(self, prompt: str) -> dict:
        """Low-level execution targeting local 14B models with robust parsing fallbacks."""
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192}
        }
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                raw_res = json.loads(response.read().decode('utf-8'))["response"]
                
                # 1. Pull the explicit thinking track out cleanly
                thinking = ""
                think_match = re.search(r'<think>(.*?)</think>', raw_res, re.DOTALL)
                if think_match:
                    thinking = think_match.group(1).strip()
                
                # 2. Extract structural markdown text block targets
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_res, re.DOTALL)
                json_str = json_match.group(1) if json_match else raw_res
                if not json_match:
                    bracket_match = re.search(r'(\{.*?\})', raw_res, re.DOTALL)
                    json_str = bracket_match.group(1) if bracket_match else raw_res
                
                # STRICT PARSING SAFETY WRAPPER: Handle raw string responses from 14B variations
                clean_json_str = json_str.strip().replace("\n", " ")
                if not clean_json_str.startswith("{") and "fix_proposal" not in clean_json_str:
                    return {
                        "thinking": thinking,
                        "action": {"fix_proposal": raw_res.replace('"', '\\"')}
                    }
                
                return {
                    "thinking": thinking,
                    "action": json.loads(clean_json_str)
                }
        except Exception as e:
            return {"thinking": "Failed pass", "action": {"status": "FAIL", "error": str(e), "fix_proposal": "Manual recovery validation trace required."}}

    def weave_chunk_to_postulate(self, chunk_id: str, chunk_text: str, target_postulate: str) -> str:
        """Analyzes a text chunk and returns structured relation metrics to a postulate."""
        prompt = f"""
        [SYSTEM]
        Analyze text relationship. Output ONLY raw JSON matching the format below.

        [INPUTS]
        Text: "{chunk_text}"
        Postulate: "{target_postulate}"

        [TASK]
        Classify if Text: ILLUSTRATES, CORROBORATES, or CHALLENGES the Postulate.
        Provide a confidence score float between 0.0 and 1.0.

        [OUTPUT FORMAT]
        ```json
        {{
          "relationship_type": "ILLUSTRATES",
          "weight": 0.85,
          "reasoning": "Short string explaining context connection."
        }}
        ```
        """
        result = self._call_ollama_reasoning(prompt)
        action = result.get("action", {})
        
        if action.get("relationship_type"):
            rel = action["relationship_type"].upper()
            weight = float(action.get("weight", 0.5))
            reasoning = action.get("reasoning", "Automated link pass.")
            
            query = f"MATCH (c:Chunk {{chunk_id: $chunk_id}}) MERGE (p:Postulate {{name: $postulate_name}}) MERGE (c)-[r:{rel}]->(p) SET r.confidence = $weight, r.reasoning = $reasoning"
            self.graph.query(query, {
                "chunk_id": chunk_id,
                "postulate_name": target_postulate,
                "weight": weight,
                "reasoning": reasoning
            })
            return f"✅ Linked chunk '{chunk_id}' -> Postulate '{target_postulate}' [{rel}]"
        return f"❌ Validation pass missed: {str(action)}"

    def execute_document_recovery_loop(self, failed_task: str, error_trace: str) -> str:
        """Dynamic recovery engine optimized with a simplified directive block."""
        prompt = f"""
        [SYSTEM]
        Graph exception recovery routing. Output ONLY valid JSON matching the format below.

        [CONTEXT]
        Failed Objective: {failed_task}
        Error Trace: {error_trace}

        [OUTPUT FORMAT]
        ```json
        {{
          "fix_proposal": "Clear structural code or database syntax fix explanation here."
        }}
        ```
        """
        result = self._call_ollama_reasoning(prompt)
        action = result.get("action", {})
        
        if isinstance(action, dict) and "fix_proposal" in action:
            return action["fix_proposal"]
        return str(action.get("error")) if "error" in action else str(result)

    def determine_retrieval_strategy(self, prompt_objective: str) -> dict:
        """Lightweight intent routing optimized for 14B models."""
        prompt = f"""
        [SYSTEM]
        Query intent router. Output ONLY valid JSON matching the format below.

        [INPUT]
        Objective: "{prompt_objective}"

        [TASK]
        If the objective requires aggregating, syncing, or consolidating ALL workspace files, select "GLOBAL_SWEEP".
        If it targets a specific topic or narrow context item, select "NARROW_VECTOR".

        [OUTPUT FORMAT]
        ```json
        {{
          "strategy": "GLOBAL_SWEEP",
          "reasoning": "Brief explanation."
        }}
        ```
        """
        result = self._call_ollama_reasoning(prompt)
        action = result.get("action", {})
        
        if isinstance(action, dict) and "strategy" in action:
            return {
                "strategy": str(action["strategy"]).upper(),
                "reasoning": str(action.get("reasoning", "AI decision pass."))
            }
        
        return {"strategy": "NARROW_VECTOR", "reasoning": "Fallback routing configuration."}

if __name__ == "__main__":
    weaver = DocumentConceptAgent()
    print("✨ Document Concept Weaving System Ready (Frameworkless Core Stack).")
