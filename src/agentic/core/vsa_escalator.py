# src/agentic/core/vsa_escalator.py
import numpy as np
import json
import hashlib
from core.llm_client import LLMClient

class VSAEpistemicEscalator:
    def __init__(self, dimension: int = 1024):
        self.dimension = dimension
        self.llm_client = LLMClient()
        self.threshold = 0.70  # Epistemic threshold: values below this trigger escalation
        
        # Initialize orthogonal hypervectors for symbolic state tracking
        np.random.seed(42)
        self.CONCEPT_KNOWN = self._generate_hypervector()
        self.CONCEPT_UNKNOWN = self._generate_hypervector()
        self.ERROR_TRAPPED = self._generate_hypervector()

    def _generate_hypervector(self) -> np.ndarray:
        """Generates a normalized, random bipolar hypervector."""
        vec = np.random.choice([-1, 1], size=self.dimension)
        return vec / np.linalg.norm(vec)

    def bind(self, vec_a: np.ndarray, vec_b: np.ndarray) -> np.ndarray:
        """Element-wise multiplication (XOR analogue) to bind concepts together."""
        return vec_a * vec_b

    def bundle(self, vec_list: list[np.ndarray]) -> np.ndarray:
        """Element-wise addition followed by normalization to merge concepts."""
        summed = np.sum(vec_list, axis=0)
        norm = np.linalg.norm(summed)
        return summed / norm if norm > 0 else summed

    def calculate_cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Measures geometric distance inside the high-dimensional logic space."""
        return float(np.dot(vec_a, vec_b))

    def evaluate_epistemic_state(self, raw_embedding: list[float], runtime_logs: str) -> dict:
        """
        Evaluates system confidence. If the similarity vector falls below 
        the threshold, it programmatically structures an escalation path.
        """
        if not raw_embedding:
            return {"status": "ESCALATE", "reason": "Empty vector space context."}
            
        query_vector = np.array(raw_embedding) / np.linalg.norm(raw_embedding)
        
        # Test structural proximity to the known concept space
        similarity = self.calculate_cosine_similarity(query_vector, self.CONCEPT_KNOWN)
        print(f"📐 [VSA Epistemic Distance Metric]: Cosine proximity calculated at: {similarity:.4f}")

        # Detect clear runtime failures inside the string trace logs
        is_broken = "unexpected keyword argument" in runtime_logs or "Traceback" in runtime_logs
        
        if similarity < self.threshold or is_broken:
            print("🚨 [VSA System Alarm]: Epistemic boundary breached. Activating Escalation Engine.")
            
            # Algebraically bind the error state into the current query matrix
            bound_error = self.bind(query_vector, self.ERROR_TRAPPED)
            
            escalation_prompt = f"""You are the Advanced Technical Escalation Engine. 
The system has encountered a functional blind spot that it does not know how to resolve. 

[REALITY ANOMALY CONTEXT]
Runtime Log: {runtime_logs}

Analyze the failure pattern step-by-step. Formulate a structured research ticket defining exactly what piece of external documentation, API signature code, or first principle is missing from our current database.
"""
            raw_ticket, _ = self.llm_client.call_local_llm(escalation_prompt)
            
            return {
                "status": "ESCALATE",
                "confidence_score": similarity,
                "bound_state_hash": hashlib.sha256(bound_error.tobytes()).hexdigest()[:8],
                "escalation_ticket": raw_ticket.strip()
            }
            
        return {"status": "RESOLVED", "confidence_score": similarity}
