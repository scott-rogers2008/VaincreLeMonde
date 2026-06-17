# src/agentic/codebase_guru/tools/agent_tools.py
from falkordb import FalkorDB
from .embedder import LocalEmbedder

class AgentTools:
    def __init__(self):
        # 1. Connect natively to your low-memory FalkorDB instance
        self.db = FalkorDB(host='localhost', port=6379)
        # 2. Select the matching codebase graph space utilized by git_sync
        self.graph = self.db.select_graph("codebase_guru")
        self.embedder = LocalEmbedder()

    def search_semantic_code(self, user_query: str, limit: int = 3) -> str:
        """
        Executes a native vector search inside FalkorDB via HNSW index lookup,
        then traces parental Method structures instantly.
        """
        vector = self.embedder.get_embedding(user_query)
        if not vector:
            return "Error: Could not generate vector embedding for the query."

        # CRITICAL FIX: The incoming prompt vector MUST be explicitly cast 
        # using vecf32($vector) within the query string parameters block!
        query = """
            CALL db.idx.vector.queryNodes('Chunk', 'embedding', $limit, vecf32($vector)) 
            YIELD node, score
            MATCH (m:Method)-[:HAS_CHUNK]->(node)
            RETURN m.name AS name, m.body AS body, score
        """
        
        results = []
        try:
            res = self.graph.query(query, {"limit": limit, "vector": vector})
            # FalkorDB returns rows unpacked within result_set matrix rows
            for row in res.result_set:
                name = row[0]
                body = row[1]
                score = float(row[2])
                results.append(f"--- Method: {name} (Score: {score:.4f}) ---\n{body}")
        except Exception as e:
            return f"Error executing FalkorDB semantic search: {str(e)}"
            
        return "\n\n".join(results) if results else "No matching code blocks found."

    def check_documentation_history(self, method_name: str) -> str:
        """Traces the historical timeline of documentation updates for a specific method."""
        query = """
            MATCH (m:Method {name: $method_name})-[:CURRENT_DOC|HISTORICAL_DOC]->(d:Documentation)
            RETURN d.text AS text, d.timestamp AS ts, d.is_active AS active
            ORDER BY d.timestamp DESC
        """
        timeline = []
        try:
            res = self.graph.query(query, {"method_name": method_name})
            for row in res.result_set:
                text_val = row[0]
                ts_val = int(row[1])
                active_val = bool(row[2])
                
                status = "CURRENT ACTIVE INTENT" if active_val else "HISTORICAL / SUPERSEDED"
                timeline.append(f"[{status} - TS: {ts_val}]\nDoc: {text_val}")
        except Exception as e:
            return f"Error querying documentation timeline: {str(e)}"
            
        return "\n\n".join(timeline) if timeline else f"No documentation versions found for '{method_name}'."

    def list_file_contents(self, file_path: str) -> str:
        """Lists all functions and structural definitions mapped inside a given file node."""
        query = """
            MATCH (f:File {path: $file_path})-[:CONTAINS]->(m:Method)
            RETURN m.name AS name, m.body_hash AS hash
        """
        methods = []
        try:
            res = self.graph.query(query, {"file_path": file_path})
            for row in res.result_set:
                name = row[0]
                body_hash = row[1]
                methods.append(f" - Method: {name}() [Hash: {body_hash[:8]}]")
        except Exception as e:
            return f"Error cataloging file structural layout: {str(e)}"
            
        if not methods:
            return f"No tracked structural components found in file '{file_path}'."
        return f"File: {file_path}\n" + "\n".join(methods)

    def close(self):
        pass
