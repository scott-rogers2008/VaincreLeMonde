# src/agentic/language_tutor/tools/linguistic.py
import spacy
from sqlalchemy import text
from .chunker import SemanticChunker
from .database_tools import db_content_loader
from .database_manager import engine

def loader(document_text: str, lang_id: int, work_id: int) -> list:
    """Divides a document into a sequence of sentences and stores them in the database."""
    chnkr = SemanticChunker()
    chunks = chnkr.chunk_text(text=document_text)
    all_sentences = []
    
    for chunk in chunks:
        sentences = sentence_splitter(chunk, lang_id)
        db_content_loader(sentences, lang_id, work_id)
        all_sentences.extend(sentences)
        
    return all_sentences

def sentence_splitter(text_block: str, lang_id: int) -> list:
    """Splits raw text segments into verified clean sentences via SpaCy pipelines."""
    if text_block.startswith("Error") or "CRITICAL_FAILURE" in text_block:
        raise ValueError(f"Cannot split sentences because the input is an error: {text_block}")
    try:
        with engine.connect() as conn:
            query = text("SELECT spacy_model FROM language WHERE id = :lang")
            result = conn.execute(query, {"lang": lang_id}).fetchone()
            if not result or not result[0]:
                raise Exception(f"No spaCy model configured for language {lang_id}")
            model_name = result[0]
            
        nlp = spacy.load(model_name)
        doc = nlp(text_block)
        sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 5]
        return sentences if sentences else ["No valid sentences found in the provided text."]
    except Exception as e:
        raise Exception(f"Linguistic processing failed: {str(e)}")
