# src/agentic/document_concept_agent.py
import os
import json
import re
import urllib.request
from datetime import date
from falkordb import FalkorDB
from utils import get_git_root
from language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

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
                    # Formulate valid structure dynamically if the model outputs conversation
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
        """Analyzes a narrative chunk and creates a structural Bayesian connection link."""
        prompt = f"""
        You are an Elite Philological Weaving Engine. Analyze how the following story text chunk
        relates to the target educational Postulate concept.

        [STORY CHUNK TEXT]
        "{chunk_text}"

        [TARGET POSTULATE CONCEPT]
        "{target_postulate}"

        Determine if this chunk倾向于 ILLUSTRATES, CORROBORATES, or CHALLENGES the postulate.
        Assign a confidence weight score between 0.0 and 1.0.

        Output exactly ONE JSON block matching this layout structure:
        ```json
        {{
          "relationship_type": "ILLUSTRATES",
          "weight": 0.85,
          "reasoning": "Operational concept explanation text."
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
        """Dynamic recovery engine for multi-lingual educational data spaces."""
        prompt = f"""
        You are the Lead Educational Knowledge Graph Architect. A data loading or retrieval operation 
        failed within our multi-lingual document graph runtime space. Review the error details below.

        [FAILED MISSION OBJECTIVE]
        {failed_task}

        [UNHANDLED DATABASE EXCEPTION TRACE]
        {error_trace}

        Provide a clear textual analysis explaining how to patch this problem context layout.
        Your response MUST include a valid 'fix_proposal' JSON key to clear internal parsers:
        ```json
        {{
          "fix_proposal": "Your thorough description detailing structural syntax solutions or code corrections goes here."
        }}
        ```
        """
        result = self._call_ollama_reasoning(prompt)
        action = result.get("action", {})
        
        if isinstance(action, dict) and "fix_proposal" in action:
            return action["fix_proposal"]
        return str(action.get("error")) if "error" in action else str(result)

if __name__ == "__main__":
    weaver = DocumentConceptAgent()
    print("✨ Document Concept Weaving System Ready (Frameworkless Core Stack).")
