# src/agentic/core/tutor_tool_router.py
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

class TutorToolRouter:
    def __init__(self, code_tools):
        # Anchor natively back to the central AgentTools module context
        self.code_tools = code_tools

    def dispatch(self, action_type: str, param: str, pillar: str) -> tuple[str, str]:
        """
        Executes the backend database tool call and returns an atomic tuple layout matching 
        (tool_output_string, cited_chunk_id).
        """
        cited_chunk = "None"
        tool_out = ""

        if action_type == "VECTOR_SEARCH":
            active_graph_space = self.code_tools.db.select_graph("document_rag_graph")
            
            # 1. Provision the native openCypher vector distance instruction
            query = """
            CALL db.idx.vector.queryNodes('Chunk', 'embedding', 1, vecf32($param_vector))
            YIELD node, score
            RETURN node.chunk_id AS identity, node.text AS text, score
            """
            
            # 2. Compute 1024D bge-m3 embeddings natively
            vector_data = get_multilingual_embedding(param)
            if vector_data and isinstance(vector_data, list):
                sanitized_vector = [float(x) for x in vector_data]
                res = active_graph_space.query(query, {"param_vector": sanitized_vector})
                
                # 3. Correctly parse the FalkorDB cell matrix result rows
                if res and res.result_set:
                    row = res.result_set[0]
                    try:
                        identity_val = row[0]
                        text_val = row[1]
                        score_val = float(row[2])
                    except Exception:
                        identity_val = "Doc-Chunk"
                        text_val = str(row)
                        score_val = 0.0
                    
                    cited_chunk = str(identity_val) if identity_val is not None else "Doc-Chunk"
                    tool_out = f"--- Verified Source Document Match: {cited_chunk} (Score: {score_val:.4f}) ---\n{str(text_val)}"
                else:
                    # Force the custom expected exception to trigger agent recovery flows
                    raise LookupError(f"Missing Essential Context: Vector index lookup for '{param}' returned 0 records.")
            else:
                tool_out = "Failed to calculate a valid document lookup vector."
                
        elif action_type == "LIST_METHODS":
            tool_out = self.code_tools.list_file_contents(param)
            
        elif action_type == "LIBRARY_SEARCH":
            tool_out = str(library_search(search_term=param))
            
        elif action_type == "GENERAL_MATRIX_ADVICE":
            tool_out = f"Navigating guidelines inside the [{pillar}] sector entries."
            
        else:
            tool_out = f"Default fallback execution channel applied for sector: {pillar}"

        return tool_out, cited_chunk
