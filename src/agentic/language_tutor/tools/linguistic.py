# tools/linguistic.py
import spacy
from smolagents import tool
from sqlalchemy import text
from .database_manager import engine

@tool
def sentence_splitter(text_block: str, lang_id: int) -> list:
    """
    Splits text into sentences using the language's specific spaCy model defined in the DB.
    Args:
        text_block: The raw text to be processed.
        lang_id: The integer ID from the language table.
    """
    try:
        # 1. Fetch the model name from the database
        with engine.connect() as conn:
            query = text("SELECT spacy_model FROM language WHERE id = :lang")
            result = conn.execute(query, {"lang": lang_id}).fetchone()
            
        if not result or not result[0]:
            return [f"Error: No spaCy model configured for language {lang_id}"]
        
        model_name = result[0]

        # 2. Process the text
        nlp = spacy.load(model_name)
        doc = nlp(text_block)
        return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]

    except Exception as e:
        return [f"Linguistic processing error: {str(e)}"]
