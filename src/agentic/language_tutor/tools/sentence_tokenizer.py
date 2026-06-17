# src/agentic/language_tutor/tools/sentence_tokenizer.py
import spacy
from sqlalchemy import text
from .database_manager import engine
from typing import List, Dict

def sentence_tokenizer_tool(text_content: str, lang_id: int) -> List[Dict]:
    """Tokenizes structural sentences to catalog lemmas and morphological variables."""
    try:
        with engine.connect() as conn:
            query = text("SELECT spacy_model FROM language WHERE id = :lang")
            model_name = conn.execute(query, {"lang": lang_id}).scalar()
            if not model_name:
                return [{"error": f"No spaCy model configured for language {lang_id}"}]
                
        nlp = spacy.load(model_name)
        doc = nlp(text_content)
        return [
            {
                "text": t.text,
                "lemma": t.lemma_,
                "pos": t.pos_,
                "index": t.i
            } for t in doc if not t.is_punct and not t.is_space
        ]
    except Exception as e:
        return [{"error": f"Linguistic processing error: {str(e)}"}]
