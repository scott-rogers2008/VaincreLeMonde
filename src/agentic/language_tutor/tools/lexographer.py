# tools/lexographer.py
from smolagents import tool
from sqlalchemy import text
from .database_manager import engine
from .embeddings import get_embeddings
from wordfreq import zipf_frequency

@tool
def definition_storage_tool(
    word: str, 
    pos_tag: str, 
    definition: str, 
    lang_id: str, 
    register_tag: str = "NEUTRAL",
    specificity: float = 0.5,
    estimated_zipf: float = None
) -> int:
    """
    Saves a curated definition with embeddings by looking up IDs for POS and Register tags.
    Args:
        word: The root lemma.
        pos_tag: The spaCy POS tag (e.g., 'NOUN', 'VERB').
        definition: The curated monolingual definition.
        embedding: List of 1024 floats from Ollama bge-m3.
        lang_id: Language code (e.g., 'DEU-ZZ-M').
        register_tag: The register tag (e.g., 'NEUTRAL', 'FORMAL').
        specificity: Score from 0.0 (very general like "thing") to 1.0 (highly technical/niche).
        estimated_zipf: The estimated log frequency (Zipf scale 0-8).
    """
    zipf = zipf_frequency(word, lang_id[:2])
    if zipf == 0 and estimated_zipf is not None:
        zipf = estimated_zipf
    elif zipf == 0:
        zipf = 1.0

    raw_embeddings = get_embeddings(definition)
    vector_list = raw_embeddings[0]
    vector_str = f"[{','.join(map(str, vector_list))}]"
    
    with engine.begin() as conn:
        # Note: using 'tag' column to match your SELECT * results
        query = text("""
            INSERT INTO dictionary_entries (
                language_id, 
                pos_id, 
                register_id, 
                word, 
                definition_monolingual, 
                definition_embedding,
                frequency_zipf,
                specificity_score
            ) VALUES (
                :lang,
                (SELECT id FROM parts_of_speech WHERE tag = :pos LIMIT 1),
                (SELECT id FROM registers WHERE tag = :reg LIMIT 1),
                :word,
                :def,
                :vec,
                :zipf,
                :spec
            ) RETURNING id
        """)
        
        return conn.execute(query, {
            "lang": lang_id,
            "pos": pos_tag,
            "reg": register_tag,
            "word": word,
            "def": definition,
            "vec": vector_str,
            "zipf": zipf,
            "spec": specificity
        }).scalar()

@tool
def dictionary_sense_lookup(
    word: str, 
    pos_tag: str, 
    context_sentence: str, 
    lang_id: str
) -> dict:
    """
    Checks if a definition for a word already exists that matches the current context.
    Returns the entry_id if a match is found, otherwise returns None.
        
    Args:
        word: The lemma or word to look up.
        pos_tag: The spaCy POS tag (e.g., 'NOUN', 'VERB').
        context_sentence: The sentence where the word appears, used for sense disambiguation.
        lang_id: The 10-char language code.
    """
    context_vector = get_embeddings(context_sentence)
    # Ensure it's a flat list of floats
    if isinstance(context_vector, list) and len(context_vector) > 0 and isinstance(context_vector[0], list):
        context_vector = context_vector[0]
    vector_str = f"[{','.join(map(str, context_vector))}]"

    with engine.connect() as conn:
        query = text("""
            SELECT id, definition_monolingual, (definition_embedding <=> :vec) AS distance
            FROM dictionary_entries 
            WHERE word = :word 
            AND pos_id = (SELECT id FROM parts_of_speech WHERE tag = :pos LIMIT 1)
            AND language_id = :lang
            ORDER BY distance ASC
            LIMIT 1
        """)
        result = conn.execute(query, {
            "word": word, 
            "pos": pos_tag, 
            "lang": lang_id, 
            "vec": vector_str
        }).fetchone()

        # Now result[2] is the distance
        if result and result[2] < 0.15:
            return {"id": result[0], "definition": result[1]}
        return None


@tool
def sentence_word_mapper(
    sentence_id: int, 
    entry_id: int, 
    indices: list, 
    is_target: bool = False
) -> str:
    """
    Links a dictionary entry to specific word positions within a sentence.

    Args:
        sentence_id: the index of the sentence
        entry_id: the id of the word or phrase in the dictionary
        indices: the list of indexes for the tokens for the word or phrase in the sentence
        is_target: is this the target word for this training
    """
    with engine.begin() as conn:
        query = text("""
            INSERT INTO sentence_word_map (sentence_id, entry_id, word_indices, is_target_word)
            VALUES (:sid, :eid, :idx, :target)
            ON CONFLICT (sentence_id, entry_id) DO UPDATE 
            SET word_indices = EXCLUDED.word_indices, is_target_word = EXCLUDED.is_target_word
        """)
        conn.execute(query, {"sid": sentence_id, "eid": entry_id, "idx": indices, "target": is_target})
        
    return f"Success: Entry {entry_id} mapped to sentence {sentence_id} at indices {indices}."
