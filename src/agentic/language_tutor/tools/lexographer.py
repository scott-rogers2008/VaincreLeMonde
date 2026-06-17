# src/agentic/language_tutor/tools/lexographer.py
from falkordb import FalkorDB
from datetime import date
from wordfreq import zipf_frequency
from .embeddings import get_embeddings
from .database_manager import engine 
from sqlalchemy import text as sa_text

# Establish a shared low-overhead connection pool target config for standalone tools
def get_falkor_graph():
    db = FalkorDB(host='localhost', port=6379)
    return db.select_graph("document_rag_graph")

def initialize_lexicon_indexes():
    """Provisions native vector index mappings for dictionary meanings inside FalkorDB."""
    try:
        graph = get_falkor_graph()
        graph.query(
            "CREATE VECTOR INDEX FOR (s:Sense) ON (s.embedding) "
            "OPTIONS {dimension: 1024, similarityFunction: 'cosine'}"
        )
        print("✅ FalkorDB native lexicon vector index verified active.")
    except Exception:
        pass

def load_dictionary_entry_to_graph(word: str, pos_tag: str, definition: str, lang_id: str, context_chunk_id: str = None) -> int:
    """
    Saves a vocabulary definition to PostgreSQL, generates a matching node cluster 
    inside FalkorDB, and links it to active story chunks via semantic edges.
    """
    zipf = zipf_frequency(word, lang_id[:2])
    if zipf == 0:
        zipf = 1.0
        
    raw_embeddings = get_embeddings(definition)
    vector_list = raw_embeddings if not isinstance(raw_embeddings, list) else raw_embeddings
    vector_str = f"[{','.join(map(str, vector_list))}]"
    
    # 1. Handle relational persistence inside your legacy PostgreSQL schema
    with engine.begin() as conn:
        sql_query = sa_text("""
            INSERT INTO dictionary_entries (language_id, pos_id, register_id, word, definition_monolingual, definition_embedding, frequency_zipf, specificity_score)
            VALUES (:lang, (SELECT id FROM parts_of_speech WHERE tag = :pos LIMIT 1), (SELECT id FROM registers WHERE tag = :reg LIMIT 1), :word, :def, :vec, :zipf, 0.5)
            RETURNING id
        """)
        postgres_entry_id = conn.execute(sql_query, {
            "lang": lang_id, "pos": pos_tag, "reg": "NEUTRAL",
            "word": word.strip().lower(), "def": definition.strip(), "vec": vector_str, "zipf": zipf
        }).scalar()

    # 2. Construct structural Lexicon Graph nodes inside FalkorDB
    initialize_lexicon_indexes()
    graph = get_falkor_graph()
    
    lexeme_query = """
        MERGE (l:Lexeme {text: $word, language: $lang})
        SET l.pos = $pos
        RETURN l
    """
    graph.query(lexeme_query, {"word": word.strip().lower(), "lang": lang_id, "pos": pos_tag})

    sense_query = """
        MATCH (l:Lexeme {text: $word, language: $lang})
        CREATE (s:Sense {
            postgres_id: $pg_id,
            definition: $def,
            embedding: vecf32($vector),
            created_at: $today
        })
        MERGE (l)-[:HAS_SENSE]->(s)
        RETURN s
    """
    graph.query(sense_query, {
        "word": word.strip().lower(), "lang": lang_id, "pg_id": int(postgres_entry_id),
        "def": definition.strip(), "vector": vector_list, "today": date.today().isoformat()
    })

    # 3. If triggered by an active story passage chunk, build an immediate edge link
    if context_chunk_id:
        link_query = """
            MATCH (c:Chunk {chunk_id: $c_id})
            MATCH (l:Lexeme {text: $word, language: $lang})-[:HAS_SENSE]->(s:Sense {postgres_id: $pg_id})
            MERGE (c)-[:CONTAINS_WORD]->(l)
            MERGE (c)-[:USES_SENSE {source: 'automated_pipeline_ingest'}]->(s)
        """
        graph.query(link_query, {
            "c_id": context_chunk_id, "word": word.strip().lower(), "lang": lang_id, "pg_id": int(postgres_entry_id)
        })

    print(f"  └── Graph Lexicon Sync complete: Linked '{word}' -> Sense Cluster ID: {postgres_entry_id}")
    return postgres_entry_id

def dictionary_sense_graph_lookup(word: str, context_sentence: str, lang_id: str) -> dict or None:
    """
    Performs a native openCypher vector distance query within FalkorDB 
    to locate a pre-existing definition matching the specific contextual meaning.
    """
    context_vector = get_embeddings(context_sentence)
    if isinstance(context_vector, list):
        context_vector = context_vector

    graph = get_falkor_graph()
    query = """
        CALL db.idx.vector.query('Sense', 'embedding', 1, vecf32($vector))
        YIELD node, score
        MATCH (l:Lexeme {text: $word, language: $lang})-[:HAS_SENSE]->(node)
        RETURN node.postgres_id AS pg_id, node.definition AS definition, score
    """
    try:
        res = graph.query(query, {"vector": context_vector, "word": word.strip().lower(), "lang": lang_id})
        for row in res.result_set:
            pg_id = row[0]
            definition = row[1]
            score = float(row[2])
            
            if score > 0.85:
                return {"id": pg_id, "definition": definition, "confidence": score}
    except Exception as e:
        print(f"⚠️ Graph semantic search lookup bypassed: {e}")
        
    return None
