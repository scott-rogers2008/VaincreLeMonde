# src/agentic/codebase_guru/tools/graph_db.py
from falkordb import FalkorDB

class CodebaseGraphManager:
    def __init__(self):
        # 1. Connect natively to your low-memory FalkorDB container via its port
        self.db = FalkorDB(host='localhost', port=6379)
        # 2. Select or create your isolated codebase structure graph space
        self.graph = self.db.select_graph("codebase_guru")
        
    def close(self):
        # FalkorDB client features automatic thread connection pooling; no manual close needed
        pass

    def initialize_indexes(self):
        """Creates the required native openCypher vector indexes inside FalkorDB."""
        # We index the 'embedding' property of Chunk nodes (768 dimensions for Nomic text)
        try:
            self.graph.create_vector_index(
                label="Chunk", 
                property="embedding", 
                dim=768, 
                distance_metric="cosine"
            )
            print("✅ FalkorDB codebase vector index verified.")
        except Exception:
            # Index already exists in container space
            pass

    def sync_file_node(self, file_path: str, file_hash: str):
        """Upserts a baseline module File node using native openCypher."""
        query = """
            MERGE (f:File {path: $file_path})
            SET f.hash = $file_hash
        """
        self.graph.query(query, {"file_path": file_path, "file_hash": file_hash})

    def sync_chunked_method_data(self, file_path: str, method_name: str, method_data: dict, vector_chunks: list):
        """Atomic codebase component structural sync pass optimized for FalkorDB."""
        body_hash = method_data["body_hash"]
        block_id_prefix = f"{file_path}:{method_name}:{body_hash[:8]}"
        
        # 1. Clear out past block instances cleanly to prevent dead clutter or duplicates
        purge_query = """
            MATCH (c:Chunk) 
            WHERE c.block_id STARTS WITH $block_prefix 
            DETACH DELETE c
        """
        self.graph.query(purge_query, {"block_prefix": block_id_prefix})
        
        # 2. Ensure parent method node exists and links back to its file context
        link_query = """
            MATCH (f:File {path: $file_path})
            MERGE (f)-[:CONTAINS]->(m:Method {name: $method_name})
            SET m.body_hash = $body_hash
        """
        self.graph.query(link_query, {
            "file_path": file_path, 
            "method_name": method_name, 
            "body_hash": body_hash
        })

        # 3. Stream structural chunks and their vector data into the container graph
        for v_info in vector_chunks:
            idx = v_info["chunk_index"]
            specific_block_id = f"{block_id_prefix}:chunk_{idx}"
            chunk_text = v_info["chunk_text"]
            raw_vector = v_info["vector"] # List of 768 floats from Nomic

            chunk_query = """
                MATCH (f:File {path: $file_path})-[:CONTAINS]->(m:Method {name: $method_name})
                CREATE (c:Chunk {
                    block_id: $specific_block_id,
                    text: $chunk_text,
                    index: $chunk_idx,
                    embedding: $vector
                })
                CREATE (m)-[:HAS_CHUNK]->(c)
            """
            self.graph.query(chunk_query, {
                "file_path": file_path,
                "method_name": method_name,
                "specific_block_id": specific_block_id,
                "chunk_text": chunk_text,
                "chunk_idx": idx,
                "vector": raw_vector
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
        res = self.graph.query(query, {"file_path": file_path})
        # Check matrix result set to evaluate if a node was deleted
        for record in res.result_set:
            return bool(record)
        return False
