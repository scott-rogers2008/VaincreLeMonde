# src/agentic/loader.py
import os
import hashlib
import requests
from datetime import date
from falkordb import FalkorDB
from .language_tutor.tools.chunker import SemanticChunker
from .utils import get_git_root

EMBED_MODEL = "bge-m3"
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
os_walk_exclude = {'.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', '.vs', '.vscode', 'node_modules', 'src'}

class MDFileChangeHandler:
    def __init__(self):
        # Connect to FalkorDB and mount an isolated graph space for Document RAG
        self.db = FalkorDB(host='localhost', port=6379)
        self.graph = self.db.select_graph("document_rag_graph")
        self.chunker = SemanticChunker()

    def _calculate_file_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _get_bge_embedding(self, text: str) -> list:
        """Fetches 1024D multi-lingual embeddings from your local model."""
        if not text.strip(): 
            return [0.0] * 1024
        try:
            res = requests.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=30)
            return res.json()["embeddings"][0] if res.status_code == 200 else [0.0] * 1024
        except Exception:
            return [0.0] * 1024

    def initialize_graph_environment(self):
        """Creates a native 1024-dimension HNSW index inside FalkorDB."""
        try:
            self.graph.query(
                "CREATE VECTOR INDEX FOR (c:Chunk) ON (c.embedding) "
                "OPTIONS {dimension: 1024, similarityFunction: 'cosine'}"
            )
            print("✅ FalkorDB multi-lingual vector indexing space active.")
        except Exception:
            pass

    def purge_document_cascade(self, relative_path: str):
        """Removes downstream semantic text nodes cleanly to avoid stale data clutter."""
        query = """
            MATCH (d:Document {path: $doc_path})
            OPTIONAL MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d)
            DETACH DELETE d, c
        """
        self.graph.query(query, {"doc_path": relative_path})

    def sync_all(self):
        """Discovers and parses markdown files using active delta hashing loops."""
        base_dir = get_git_root(os.curdir)
        self.initialize_graph_environment()
        
        # Pull active graph hashes into memory to skip unchanged scripts
        db_hashes = {}
        try:
            res = self.graph.query("MATCH (d:Document) RETURN d.path AS path, d.hash AS hash")
            for row in res.result_set: 
                db_hashes[str(row[0]).strip('"')] = str(row[1]).strip('"')
        except Exception:
            pass

        for root, dirs, files in os.walk(base_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in os_walk_exclude]
            
            # Map structural directories via openCypher
            for d in dirs:
                dir_path = os.path.relpath(os.path.join(root, d), base_dir).replace("\\", "/")
                parent_path = os.path.relpath(root, base_dir).replace("\\", "/")
                query = """
                    MERGE (p:Directory {path: $parent_path})
                    MERGE (c:Directory {path: $child_path})
                    SET c.name = $name
                    MERGE (c)-[:CHILD_OF]->(p)
                """
                self.graph.query(query, {"parent_path": parent_path, "child_path": dir_path, "name": d})

            for file in files:
                if ".aider" in file or not file.endswith('.md'): 
                    continue
                    
                full_md_path = os.path.join(root, file)
                db_rel_path = os.path.relpath(full_md_path, base_dir).replace("\\", "/")
                db_parent_dir = os.path.relpath(root, base_dir).replace("\\", "/")
                
                try:
                    with open(full_md_path, 'r', encoding='utf-8') as f: 
                        document_text = f.read()
                except UnicodeDecodeError:
                    with open(full_md_path, 'r', encoding='cp1252', errors='replace') as f: 
                        document_text = f.read()

                live_file_hash = self._calculate_file_hash(document_text)
                if db_rel_path in db_hashes and db_hashes[db_rel_path] == live_file_hash:
                    print(f"  ⏭️ Skipping unchanged file: '{db_rel_path}'")
                    continue
                    
                print(f"  🔄 Changes detected. Indexing document via multi-lingual model...")
                self.purge_document_cascade(db_rel_path)
                
                # Pass clean ISO string properties to track modification states precisely
                iso_today = date.today().isoformat()
                doc_query = """
                    MATCH (dir:Directory {path: $parent_path})
                    MERGE (d:Document {path: $doc_path})
                    SET d.title = $title,
                        d.hash = $file_hash,
                        d.last_update = $today,
                        d.source = $source
                    MERGE (d)-[:CHILD_OF]->(dir)
                """
                self.graph.query(doc_query, {
                    "parent_path": db_parent_dir, "doc_path": db_rel_path, "title": file,
                    "file_hash": live_file_hash, "today": iso_today, "source": "local_workspace_import"
                })

                # Chunk and embed paragraphs using the multi-lingual sliding window configuration
                chunks = self.chunker.chunk_text(text=document_text)
                for seq, chunk_body in enumerate(chunks):
                    chunk_uuid = f"{db_rel_path}:chunk_{seq}"
                    bge_vector = self._get_bge_embedding(chunk_body)
                    
                    # FIXED: Wrapped raw float list in vecf32() inside openCypher call
                    chunk_query = """
                        MATCH (d:Document {path: $doc_path})
                        CREATE (c:Chunk {
                            chunk_order: $seq,
                            text: $text,
                            chunk_id: $chunk_uuid,
                            embedding: vecf32($vector)
                        })
                        CREATE (c)-[:FROM_DOCUMENT]->(d)
                    """
                    self.graph.query(chunk_query, {
                        "doc_path": db_rel_path, "seq": seq, "text": chunk_body,
                        "chunk_uuid": chunk_uuid, "vector": bge_vector
                    })
                print(f"  └── Ingestion complete. Created {len(chunks)} multi-lingual search chunks.")
        print("✨ Document Knowledge Graph successfully synchronized with FalkorDB!")

if __name__ == "__main__":
    md_handler = MDFileChangeHandler()
    md_handler.sync_all()
