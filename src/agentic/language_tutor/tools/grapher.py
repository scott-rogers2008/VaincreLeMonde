# src/agentic/language_tutor/tools/grapher.py
from falkordb import FalkorDB
from utils import get_git_root
from datetime import date
import ollama
import os
import re

LINK_PATTERN = r'\[\[([^\]]*?)\]\]|\[[^\]]*?\]\((.*?\.[a-zA-Z0-9]+)\)'
EMBED_MODEL = "bge-m3"

class KnowledgeGrapher:
    def __init__(self, model_name=EMBED_MODEL, link_pattern=LINK_PATTERN):
        self.link_pattern = link_pattern
        self.model_name = model_name
        
        # 1. Connect natively to your low-memory FalkorDB instance
        self.db = FalkorDB(host='localhost', port=6379)
        # 2. Select or create the isolated Document RAG Graph space
        self.graph = self.db.select_graph("document_rag_graph")

    def _clean_text_for_bge(self, text: str) -> str:
        """Strips syntax that causes numerical stability (NaN) 500 crashes in Ollama BGE-M3."""
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\|[\s\-:|]+\|', '', text)
        text = re.sub(r'-{2,}', ' ', text)
        text = re.sub(r'={2,}', ' ', text)
        text = re.sub(r'(?m)^#+\s+', ' ', text)
        return " ".join(text.split())

    def create_vector_index(self):
        """Provisions a native vector index directly inside FalkorDB."""
        try:
            self.graph.query(
                "CREATE VECTOR INDEX FOR (c:Chunk) ON (c.embedding) "
                "OPTIONS {dimension: 1024, similarityFunction: 'cosine'}"
            )
            print("✅ FalkorDB chunk vector index verified.")
        except Exception:
            # Index already exists in container space
            pass

    def create_node_with_links(self, chunks, metadata):
        """Generates document nodes, text chunks, and relational graph paths inside FalkorDB."""
        self.create_vector_index()
        seq = 0
        
        for chunk in chunks:
            cleaned = self._clean_text_for_bge(chunk)
            if not cleaned.strip():
                vector = [0.0] * 1024
            else:
                vector = ollama.embed(model=self.model_name, input=cleaned)["embeddings"][0]
                
            metadata["seq"] = seq

            # CRITICAL FIX: The vector property MUST be cast with vecf32() inside the openCypher block
            chunk_query = """
                MERGE (d:Chunk {chunk_order: $seq, title: $title, source: $source})
                SET d.embedding = vecf32($vector), 
                    d.author = $author, 
                    d.text = $text, 
                    d.priority = 0.5
            """
            self.graph.query(chunk_query, {
                "seq": seq, "title": metadata["title"], "source": metadata["source"],
                "vector": vector, "author": metadata["author"], "text": chunk
            })
            seq += 1

        # Create the base document metadata node using clean ISO date strings
        iso_today = date.today().isoformat()
        doc_query = """
            MERGE (n:Document {title: $title, author: $author, path: $path})
            SET n.source = $source, 
                n.version = 0.1, 
                n.priority = 0.5, 
                n.confidence_score = 0.5, 
                n.stability_score = 0.5, 
                n.utility_score = 0.0, 
                n.sample_size = 0, 
                n.last_update = $today, 
                n.stability = 'work in progress', 
                n.type = $type
            RETURN n
        """
        self.graph.query(doc_query, {
            "title": metadata["title"], "author": metadata["author"], "path": metadata["path"],
            "source": metadata["source"], "type": metadata["type"], "today": iso_today
        })

        # Link sequential chunks and map them back to the parent Document node
        next_chunk_query = """
            MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source})
            MATCH (b:Chunk {chunk_order: $next, title: $title, source: $source})
            MERGE (a)-[:NEXT_CHUNK]->(b)
        """
        from_doc_query = """
            MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source})
            MATCH (b:Document {source: $source, title: $title})
            MERGE (a)-[:FROM_DOCUMENT]->(b)
        """

        for i in range(len(chunks)):
            self.graph.query(from_doc_query, {"seq": i, "title": metadata["title"], "source": metadata["source"]})
            if i < len(chunks) - 1:
                self.graph.query(next_chunk_query, {
                    "seq": i, "title": metadata["title"], "source": metadata["source"], "next": i + 1
                })

            # Extract links and handle cross-document routing references
            content = chunks[i]
            links = re.findall(self.link_pattern, content)
            for internal, standard in links:
                target_raw = internal or standard
                if target_raw.endswith(".md"):
                    current_dir = os.path.basename(metadata["title"])
                    base_dir = get_git_root(os.curdir)
                    predicted_target_path = os.path.normpath(os.path.join(current_dir, target_raw))
                    target_path = os.path.join(base_dir, predicted_target_path.lstrip('\\/'))
                    path = os.path.dirname(target_path)

                    link_query = """
                        MATCH (c:Chunk {chunk_order: $seq, title: $current_title})
                        MERGE (t:Document {title: $title, author: $author, path: $path, source: $source})
                        MERGE (c)-[:REFERENCES]->(t)
                    """
                    self.graph.query(link_query, {
                        "seq": i, "current_title": metadata["title"], "title": target_path,
                        "author": metadata["author"], "path": path, "source": metadata["source"]
                    })

            # Handle Keyword entity node extraction linkages
            keywords = self.extract_keywords(chunks[i])
            for keyword in keywords:
                self.graph.query("MERGE (k:Keyword {name: $keyword})", {"keyword": keyword})
                mention_query = """
                    MATCH (c:Chunk {chunk_order: $seq, title: $current_title})
                    MATCH (k:Keyword {name: $keyword})
                    MERGE (c)-[:MENTIONS]->(k)
                """
                self.graph.query(mention_query, {"seq": i, "current_title": metadata["title"], "keyword": keyword})

    def extract_keywords(self, text):
        # Kept abstract to match your original implementation template
        keywords = []
        return list(keywords)
