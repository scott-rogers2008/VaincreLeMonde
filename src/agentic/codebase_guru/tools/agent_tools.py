from tools.graph_db import CodebaseGraphManager
from tools.embedder import LocalEmbedder

class AgentTools:
    def __init__(self):
        self.db = CodebaseGraphManager()
        self.embedder = LocalEmbedder()

    def search_semantic_code(self, user_query: str, limit: int = 3) -> str:
        """
        Uses Nomic embeddings to look up matching method implementations inside Neo4j.
        """
        vector = self.embedder.get_embedding(user_query)
        if not vector:
            return "Error: Could not generate vector embedding for the query."

        cypher = """
        CALL db.index.vector.queryNodes('method_vector_index', $limit, $vector)
        YIELD node, score
        RETURN node.name AS name, node.body AS body, score
        """
        
        results = []
        with self.db.driver.session() as session:
            res = session.run(cypher, vector=vector, limit=limit)
            for record in res:
                results.append(f"--- Method: {record['name']} (Score: {record['score']:.4f}) ---\n{record['body']}")
        
        return "\n\n".join(results) if results else "No matching code blocks found."

    def check_documentation_history(self, method_name: str) -> str:
        """
        Traces the historical timeline of documentation updates for a specific method
        to catch documentation drift or architectural intent updates.
        """
        cypher = """
        MATCH (m:Method {name: $method_name})
        MATCH (m)-[:CURRENT_DOC|HISTORICAL_DOC]->(d:Documentation)
        RETURN d.text AS text, d.timestamp AS ts, d.is_active AS active
        ORDER BY d.timestamp DESC
        """
        
        timeline = []
        with self.db.driver.session() as session:
            res = session.run(cypher, method_name=method_name)
            for record in res:
                status = "CURRENT ACTIVE INTENT" if record['active'] else "HISTORICAL / SUPERSEDED"
                timeline.append(f"[{status} - TS: {record['ts']}]\nDoc: {record['text']}")
                
        return "\n\n".join(timeline) if timeline else f"No documentation versions found for '{method_name}'."

    def list_file_contents(self, file_path: str) -> str:
        """
        Lists all functions and structural definitions found within a specific mapped file.
        """
        cypher = """
        MATCH (f:File {path: $file_path})-[:CONTAINS]->(m:Method)
        RETURN m.name AS name, m.body_hash AS hash
        """
        
        methods = []
        with self.db.driver.session() as session:
            res = session.run(cypher, file_path=file_path)
            for record in res:
                methods.append(f" - Method: {record['name']}() [Hash: {record['hash'][:8]}]")
                
        if not methods:
            return f"No tracked structural components found in file '{file_path}'."
        return f"File: {file_path}\n" + "\n".join(methods)

    def close(self):
        self.db.close()
