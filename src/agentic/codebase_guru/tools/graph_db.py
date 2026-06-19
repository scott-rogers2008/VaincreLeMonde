# src/agentic/codebase_guru/tools/graph_db.py
from falkordb import FalkorDB

class CodebaseGraphManager:
    def __init__(self):
        self.db = FalkorDB(host='localhost', port=6379)
        self.graph = self.db.select_graph("codebase_guru")

    def close(self):
        pass

    def initialize_indexes(self):
        try:
            self.graph.create_vector_index(
                label="Chunk", property="embedding", dim=768, distance_metric="cosine"
            )
            print("✅ FalkorDB codebase vector index verified.")
        except Exception:
            pass

    def sync_file_node(self, file_path: str, file_hash: str):
        query = """
        MERGE (f:File {path: $file_path}) SET f.hash = $file_hash
        """
        self.graph.query(query, {"file_path": file_path, "file_hash": file_hash})

    def sync_chunked_method_data(self, file_path: str, method_name: str, method_data: dict, vector_chunks: list):
        body_hash = method_data["body_hash"]
        block_id_prefix = f"{file_path}:{method_name}:{body_hash[:8]}"
        
        purge_query = """
        MATCH (c:Chunk) WHERE c.block_id STARTS WITH $block_prefix DETACH DELETE c
        """
        self.graph.query(purge_query, {"block_prefix": block_id_prefix})

        link_query = """
        MATCH (f:File {path: $file_path})
        MERGE (f)-[:CONTAINS]->(m:Method {name: $method_name})
        SET m.body_hash = $body_hash
        """
        self.graph.query(link_query, {
            "file_path": file_path, "method_name": method_name, "body_hash": body_hash
        })

        for v_info in vector_chunks:
            idx = v_info["chunk_index"]
            specific_block_id = f"{block_id_prefix}:chunk_{idx}"
            chunk_text = v_info["chunk_text"]
            raw_vector = v_info["vector"]
            
            chunk_query = """
            MATCH (f:File {path: $file_path})-[:CONTAINS]->(m:Method {name: $method_name})
            CREATE (c:Chunk {
                block_id: $specific_block_id, text: $chunk_text, index: $chunk_idx, embedding: vecf32($vector)
            })
            CREATE (m)-[:HAS_CHUNK]->(c)
            """
            self.graph.query(chunk_query, {
                "file_path": file_path, "method_name": method_name,
                "specific_block_id": specific_block_id, "chunk_text": chunk_text,
                "chunk_idx": idx, "vector": raw_vector
            })

    def purge_file_cascade(self, file_path: str) -> bool:
        """Removes a File node and all downstream method chunks atomically from FalkorDB."""
        query = """
        MATCH (f:File {path: $file_path})
        OPTIONAL MATCH (f)-[:CONTAINS]->(m:Method)
        OPTIONAL MATCH (m)-[:HAS_CHUNK]->(c:Chunk)
        DETACH DELETE f, m, c
        RETURN count(f) > 0 AS purged
        """
        try:
            res = self.graph.query(query, {"file_path": file_path})
            # CRITICAL FIX: Extract the actual cell content out of the result matrix matrix
            if res.result_set:
                first_row = res.result_set[0]
                return bool(first_row[0])
        except Exception as e:
            print(f"❌ FalkorDB cascade execution failed: {e}")
        return False
