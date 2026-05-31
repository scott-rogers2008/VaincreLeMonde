from neo4j import GraphDatabase
from utils import get_git_root
from datetime import date
import ollama
import os
import re

LINK_PATTERN = r'\[\[([^\]]*?)\]\]|\[[^\]]*?\]\((.*?\.[a-zA-Z0-9]+)\)'
EMBED_MODEL = "bge-m3"

class KnowledgeGrapher:
    def __init__(self, model_name = EMBED_MODEL, link_pattern= LINK_PATTERN):
        self.link_pattern = link_pattern
        self.model_name = model_name

        # Set up Neo4j with credentials from environment variables
        neo4j_url = os.environ.get("NEO4J_URL")
        username = os.environ.get("NEO4J_USERNAME")
        password = os.environ.get("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(neo4j_url, auth=(username, password))

    def _clean_text_for_bge(self, text: str) -> str:
        """Strips syntax that causes numerical stability (NaN) 500 crashes in Ollama BGE-M3."""
        # 1. Remove markdown images and link text syntax
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 2. Strip heavy markdown table walls (|---|) and markdown headers which mess with positional math
        text = re.sub(r'\|[\s\-:|]+\|', '', text)
        text = re.sub(r'-{2,}', ' ', text)
        text = re.sub(r'={2,}', ' ', text)
        text = re.sub(r'(?m)^#+\s+', ' ', text)
        # 3. Collapse aggressive tab spaces and clean lines
        return " ".join(text.split())
    
    def create_vector_index(self, tx):
        # 'vector_index' matches your LangChain snippet's index_name
        tx.run("""
        CREATE VECTOR INDEX `vector_index` IF NOT EXISTS
        FOR (n:Chunk) ON (n.embedding)
        OPTIONS {indexConfig: {
        `vector.dimensions`: 1024,
        `vector.similarity_function`: 'cosine'
        }}
        """)
    
    def create_node_with_links(self, chunks, metadata):
        with self.driver.session() as session:
            session.execute_write(self.create_vector_index)

            seq = 0
            unique_ids = [None] * len(chunks)
            for chunk in chunks:
                cleaned = self._clean_text_for_bge(chunk)
                if not cleaned.strip():
                    # Option A: Use a zero-vector if you still want to index empty nodes
                    vector = [0.0] * 1024 
                    # Option B: Alternatively, use a placeholder token like: cleaned = "[empty]"
                else:
                    vector = ollama.embed(model=self.model_name, input=cleaned)["embeddings"][0]
                metadata["seq"] = seq
                unique_ids[seq] = f"{metadata['source']}_{metadata['title']}_chunk_{seq}"
                # Save text, vector AND metadata properties to the node
                session.run("""
                    MERGE (d:Chunk {chunk_order: $seq, title: $title, source: $source})
                    SET d.embedding = $vector,
                        d.author = $author,
                        d.text = $text,
                        d.priority = 0.5
                    """, 
                    text=chunk,
                    vector=vector, 
                    author=metadata["author"], 
                    source=metadata["source"], 
                    title=metadata["title"], 
                    seq=seq
                )
                seq += 1

            # Create the base document node
            nquery = """
            MERGE (n:Document {title: $title, author: $author, path: $path})
            SET n.source = $source,
                n.version = 0.1,
                n.priority = 0.5,
                n.confidence_score = 0.5,
                n.stability_score = 0.5,
                n.utility_score = 0.0,
                n.sample_size = 0,
                n.last_update = $today,
                n.stability = "work in progress",
                n.type = $type,
                n.history = []
            RETURN n
            """
            session.run(nquery, **{"title"  : metadata["title"],
                                   "author": metadata["author"],
                                   "path"  : metadata["path"],
                                   "source": metadata["source"],
                                   "type"  : metadata["type"],
                                   "today" : date.today()
                                  })
            
            nquery = """
            MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source}), (b:Chunk {chunk_order: $next, title: $title, source: $source})
            CREATE (a)-[:NEXT_CHUNK]->(b)
            RETURN a, b
            """
            dquery = """
            MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source}), (b:Document {source: $source, title: $title})
            CREATE (a)-[:FROM_DOCUMENT]->(b)
            RETURN a, b
            """

            # Extract keywords or entities from each chunk and connect nodes
            for i in range(len(chunks)):
                session.run(dquery, **{"seq":i, "title":metadata["title"], "source":metadata["source"]})
                if i < len(chunks) - 1:
                    session.run(nquery, **{"seq":i, "title":metadata["title"], "source":metadata["source"], "next":i+1})
                keywords = self.extract_keywords(chunks[i])
                content = chunks[i]
                links = re.findall(self.link_pattern, content)

            for internal, standard in links:
                target_raw = internal or standard

                if target_raw.endswith(".md"):
                    current_dir = os.path.basename(metadata["title"])
                    base_dir = get_git_root(os.curdir)
                    predicted_target_path = os.path.normpath(os.path.join(current_dir, target_raw))
                    target_path = os.path.join(base_dir, predicted_target_path.lstrip('\\/'))
                    print("Joining", base_dir, "to", predicted_target_path, "==",  target_path)
                    path = os.path.dirname(target_path)

                    link_query = """
                    MATCH (c:Chunk {chunk_order: $seq, title: $current_title})
                    // MERGE ensures the node exists even if loader.py hasn't reached it yet
                    MERGE (t:Document {title: $title, author: $author, path: $path, source: $source})
                    MERGE (c)-[:REFERENCES]->(t)
                    """
                    
                    session.run(link_query, **{
                        "seq": i,
                        "current_title": metadata["title"],
                        "title": target_path,
                        "author":metadata["author"],
                        "path": path,
                        "source": metadata["source"]
                    })

                for keyword in keywords:
                    # Create a central 'Keyword' node if it doesn't exist
                    keyword_node = session.run(f"MATCH (k:Keyword {{name: '{keyword}'}}) RETURN k", **{"keyword": keyword})
                    if not keyword_node:
                        session.run(f"CREATE (k:Keyword {{name: '{keyword}'}})", **{"keyword": keyword})

                    # Create a relationship between the chunk and the 'Keyword' node
                    session.run(f"""MATCH (c:Chunk {{chunk_order: $seq, title: $current_title}}), 
                                     (k:Keyword {{name: $keyword}}) 
                                     MERGE (c)-[:MENTIONS]->(k)""", 
                                     **{"seq": i, "current_title": metadata["title"]})
        return 


    def extract_keywords(self, text):
        # Return empty set for now.
        keywords = []
        return list(keywords)
