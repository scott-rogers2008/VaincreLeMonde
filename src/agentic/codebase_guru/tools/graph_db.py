# src/agentic/codebase_guru/tools/graph_db.py

import time
import os
from neo4j import GraphDatabase

neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

class CodebaseGraphManager:
    def __init__(self, uri=neo4j_url, auth=(username, password)):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def initialize_indexes(self):
        """Creates the required constraints and vector indexes in Neo4j."""
        with self.driver.session() as session:
            # 1. Unique Constraints to prevent duplicate active entities
            session.run("CREATE CONSTRAINT UNIQUE_FILE_PATH IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
            
            # 2. Vector Index for Code Methods (Nomic-embed-text outputs 768 dimensions)
            session.run("""
                CREATE VECTOR INDEX method_vector_index IF NOT EXISTS
                FOR (m:Method) ON (m.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 768,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """)
            
            # 3. Vector Index for Documentation
            session.run("""
                CREATE VECTOR INDEX doc_vector_index IF NOT EXISTS
                FOR (d:Documentation) ON (d.embedding)
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: 768,
                        `vector.similarity_function`: 'cosine'
                    }
                }
            """)
            print("✅ Constraints and vector indexes verified.")

    def sync_method_and_docs(self, file_path: str, method_data: dict, body_vector: list, doc_vector: list):
        """
        Inserts/updates a code method. If the docstring changes, it archives
        the old documentation using a historical version chain.
        """
        timestamp = int(time.time())
        
        query = """
        // 1. Ensure parent file exists
        MATCH (f:File {path: $file_path})
        
        // 2. Merge the Method node uniquely within this file
        MERGE (f)-[:CONTAINS]->(m:Method {name: $method_name})
        ON CREATE SET 
            m.body = $body,
            m.body_hash = $body_hash,
            m.embedding = $body_vector,
            m.created_at = $timestamp
        ON MATCH SET
            m.body = $body,
            m.body_hash = $body_hash,
            m.embedding = $body_vector,
            m.updated_at = $timestamp

        // 3. Process Documentation Layer with a subquery
        WITH m, f
        OPTIONAL MATCH (m)-[current_rel:CURRENT_DOC]->(old_doc:Documentation)
        
        // Use a conditional block to handle doc creation if none exists
        FOREACH (_ IN CASE WHEN old_doc IS NULL AND $doc_text <> "" THEN [1] ELSE [] END |
            CREATE (new_doc:Documentation {
                text: $doc_text,
                hash: $doc_hash,
                embedding: $doc_vector,
                timestamp: $timestamp,
                is_active: true
            })
            CREATE (m)-[:CURRENT_DOC]->(new_doc)
        )
        
        // Use a conditional block to handle documentation version updates
        FOREACH (_ IN CASE WHEN old_doc IS NOT NULL AND old_doc.hash <> $doc_hash AND $doc_text <> "" THEN [1] ELSE [] END |
            // Archive old relationship
            DELETE current_rel
            CREATE (m)-[:HISTORICAL_DOC]->(old_doc)
            SET old_doc.is_active = false
            
            // Create new active documentation version
            CREATE (new_doc:Documentation {
                text: $doc_text,
                hash: $doc_hash,
                embedding: $doc_vector,
                timestamp: $timestamp,
                is_active: true
            })
            CREATE (m)-[:CURRENT_DOC]->(new_doc)
            CREATE (new_doc)-[:SUPERSEDES]->(old_doc)
        )
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                file_path=file_path,
                method_name=method_data["name"],
                body=method_data["body"],
                body_hash=method_data["body_hash"],
                body_vector=body_vector,
                doc_text=method_data["docstring"],
                doc_hash=method_data["doc_hash"],
                doc_vector=doc_vector,
                timestamp=timestamp
            )

    def sync_file_node(self, file_path: str, file_hash: str):
        """Upserts a baseline File module node."""
        query = """
        MERGE (f:File {path: $file_path})
        SET f.hash = $file_hash
        """
        with self.driver.session() as session:
            session.run(query, file_path=file_path, file_hash=file_hash)

    def sync_chunked_method_data(self, file_path: str, method_name: str, method_data: dict, vector_chunks: list):
        """
        Inserts parent method structures and isolates multi-vector chunks
        using a unique block ID hash to prevent cross-over overwrites.
        """
        with self.driver.session() as session:
            # 1. Generate a unique ID specific to this precise method/class combination
            # This stops a method query pass from accidentally wiping out its parent class node data!
            block_id = f"{file_path}:{method_name}:{method_data['body_hash'][:8]}"

            # Clean out past chunk versions specific ONLY to this exact block instance
            session.run("""
                MATCH (c:Chunk {block_id: $block_id})
                DETACH DELETE c
            """, block_id=block_id)

            # 2. Iterate and append all vector block instances cleanly
            for v_info in vector_chunks:
                query = """
                MATCH (f:File {path: $file_path})
                MERGE (f)-[:CONTAINS]->(m:Method {name: $method_name})
                SET m.body_hash = $body_hash
                
                CREATE (c:Chunk {
                    block_id: $block_id,
                    text: $chunk_text,
                    index: $chunk_idx,
                    embedding: $vector
                })
                CREATE (m)-[:HAS_CHUNK]->(c)
                """
                session.run(
                    query,
                    file_path=file_path,
                    method_name=method_name,
                    body_hash=method_data["body_hash"],
                    block_id=block_id,
                    chunk_text=v_info["chunk_text"],
                    chunk_idx=v_info["chunk_index"],
                    vector=v_info["vector"]
                )

    def purge_file_cascade(self, file_path: str) -> bool:
        """
        Safely removes a File node and all of its associated structural Methods, 
        Chunks, and Documentation nodes to prevent dead clutter in the graph network.
        """
        query = """
        MATCH (f:File {path: $file_path})
        // 1. Trace and detach any related structural components
        OPTIONAL MATCH (f)-[:CONTAINS]->(m:Method)
        OPTIONAL MATCH (m)-[:HAS_CHUNK]->(c:Chunk)
        OPTIONAL MATCH (m)-[:CURRENT_DOC|HISTORICAL_DOC]->(d:Documentation)
        
        // 2. Clear out the entire connected subgraph chunk sequence cleanly
        DETACH DELETE f, m, c, d
        RETURN count(f) > 0 AS purged
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, file_path=file_path)
                record = result.single()
                return record["purged"] if record else False
        except Exception as e:
            print(f"❌ Failed graph cascade purge pass for '{file_path}': {e}")
            return False
