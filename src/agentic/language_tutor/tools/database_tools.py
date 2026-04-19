# tools/database_tools.py
from smolagents import tool
from sqlalchemy import text
from .database_manager import engine
from .embeddings import get_embeddings

@tool
def db_content_loader(sentences: list, lang_id: int, work_id: int) -> str:
    """
    Inserts an ordered list of sentences into the 'sentences' table linked to a specific work.
    Args:
        sentences: A list of raw text sentences in chronological order.
        lang_id: The integer ID from the language table.
        work_id: The integer ID of the story/chapter from the literary_works table.
    """
    success_count = 0
    try:
        raw_embeddings = get_embeddings(sentences)
        with engine.connect() as conn:
            for i, sentence in enumerate(sentences):
                vector_str = f"[{','.join(map(str, raw_embeddings[i]))}]"
                query = text("""
                    INSERT INTO sentences (language_id, work_id, full_text, text_embedding, sentence_order)
                    VALUES (:lang, :work, :text, :embedding, :order)
                """)
                conn.execute(query, {
                    "lang": lang_id,
                    "work": work_id,
                    "text": sentence,
                    "embedding": vector_str,
                    "order": i  # Preserves the narrative flow
                })
                success_count += 1
            conn.commit()
        return f"Successfully loaded {success_count} sentences into Work ID {work_id} ({lang_id})."
    except Exception as e:
        return f"Database Error: {str(e)}"

@tool
def db_content_reader(work_id: int) -> list:
    """
    Reads all sentences for a specific work, perfectly ordered from start to finish.
    Args:
        work_id: The ID of the story or chapter to retrieve.
    """
    try:
        with engine.connect() as conn:
            # We ORDER BY sentence_order to ensure the story isn't jumbled
            result = conn.execute(
                text("""
                    SELECT full_text 
                    FROM sentences 
                    WHERE work_id = :work 
                    ORDER BY sentence_order ASC
                """),
                {"work": work_id}
            )
            return [row[0] for row in result.fetchall()]
    except Exception as e:
        return [f"Error reading database: {str(e)}"]

@tool
def get_language_id(search_term: str) -> str:
    """
    Looks up the correct id in the 'language' table using a name or era.
    Args:
        search_term: A search string like 'Korean', 'Shakespeare', or 'Modern German'.
    """
    try:
        with engine.connect() as conn:
            # We search across English name, Native name, and ID code for flexibility
            query = text("""
                SELECT id, iso_639_1, iso_639_3, name_english, name_native, spacy_model
                FROM language
                WHERE name_english ILIKE :term 
                   OR name_native ILIKE :term
                   OR iso_639_3 ILIKE :term 
                   OR iso_639_1 ILIKE :term
                LIMIT 1
            """)
            result = conn.execute(query, {"term": f"%{search_term}%"}).fetchone()
            
            if result:
                return (f"Found: {result.id} ({result.name_english} / {result.name_native}). ")
            return "No matching language code found. Please ask the user for clarification."
    except Exception as e:
        return f"Database Error: {str(e)}"
