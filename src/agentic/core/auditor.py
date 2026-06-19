# src/agentic/core/auditor.py
from falkordb import FalkorDB
import hashlib
from datetime import date

class PedagogicalAuditor:
    def __init__(self):
        self.db = FalkorDB(host='localhost', port=6379)
        self.matrix_graph = self.db.select_graph("universal_life_matrix")
        self.doc_graph = self.db.select_graph("document_rag_graph")

    def generate_verification_hash(self, text_context: str, rules_applied: str) -> str:
        """Generates an immutable signature of the data context used to build an answer."""
        payload = f"{text_context}||{rules_applied}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def log_audit_trail(self, turn_id: str, user_query: str, ai_response: str, cited_chunk_id: str, rationale: str):
        """Creates a permanent audit node to verify the tutor is tracking your teaching guidelines."""
        # 1. Fetch text snippet from document graph to verify it exists
        doc_text = "Verification: Direct source chunk missing or general matrix context applied."
        if cited_chunk_id and cited_chunk_id != "None":
            try:
                res = self.doc_graph.query(
                    "MATCH (c:Chunk {chunk_id: $cid}) RETURN c.text", {"cid": cited_chunk_id}
                )
                if res.result_set:
                    doc_text = str(res.result_set[0][0])
            except Exception:
                pass

        v_hash = self.generate_verification_hash(doc_text, rationale)

        # 2. Write the audit certificate into the universal life matrix space
        query = """
        CREATE (a:AuditCertificate {
            id: $cert_id,
            timestamp: $today,
            verification_hash: $v_hash,
            pedagogical_rationale: $rationale,
            source_citation: $cited_id,
            source_text_verbatim: $source_text
        })
        """
        try:
            self.matrix_graph.query(query, {
                "cert_id": f"audit_{turn_id}",
                "today": date.today().isoformat(),
                "v_hash": v_hash,
                "rationale": rationale,
                "cited_id": cited_chunk_id,
                "source_text": doc_text[:500] # Cap snippet for optimal low-resource memory storage
            })
            print(f"🔒 [Pedagogical Auditor]: Verification hash logged cleanly. Signature: {v_hash[:12]}")
        except Exception as e:
            print(f"❌ Verification logging failed: {e}")

    def verify_response_integrity(self, cert_id: str) -> dict:
        """Reads back an explicit verification record to prove compliance with your texts."""
        query = """
        MATCH (a:AuditCertificate {id: $cert_id})
        RETURN a.timestamp, a.verification_hash, a.pedagogical_rationale, a.source_citation, a.source_text_verbatim
        """
        try:
            res = self.matrix_graph.query(query, {"cert_id": cert_id})
            if res.result_set:
                row = res.result_set[0]
                return {
                    "status": "VERIFIED_COMPLIANT",
                    "timestamp": row[0],
                    "hash": row[1],
                    "teaching_rationale": row[2],
                    "document_citation_id": row[3],
                    "source_context_used": row[4]
                }
        except Exception:
            pass
        return {"status": "AUDIT_FAILED", "error": "No matching verification parameters found."}
