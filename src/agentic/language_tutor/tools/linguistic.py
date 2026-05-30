# tools/linguistic.py

import spacy
from smolagents import tool
from sqlalchemy import text
from .chunker import SemanticChunker
from .database_tools import db_content_loader
from .database_manager import engine

@tool
def loader(document_text: str, lang_id: int, work_id: int) -> list:
    """
    Devides a document into a list of chunks, then sentences, and loads them into the database
    Args:
        document_text: The text of the document as one long string.
        lang_id: The integer ID from the language table.
        work_id: The integer ID of the story/chapter from the literary_works table.
    """
    from smolagents import LiteLLMModel
    from agents.philologist import create_philologist_agent
    
    model = LiteLLMModel(model_id="ollama/qwen3:8b")
    philologist = create_philologist_agent(model)
    
    chnkr = SemanticChunker()
    chunks =  chnkr.chunk_text(text = document_text)
    for chunk in chunks:
        sentences = sentence_splitter(chunk, lang_id)
        db_content_loader(sentences, lang_id, work_id)
        for sentence in sentences:
            philologist.run(f"Find wich words or phases need to be added to the dictionary in the sentence:\n {sentence}\n")


@tool
def sentence_splitter(text_block: str, lang_id: int) -> list:
    """
    Splits text into sentences using the language's specific spaCy model defined in the DB.
    Args:
        text_block: The raw text to be processed.
        lang_id: The integer ID from the language table.
    """
    # CRITICAL: If the previous tool returned an error, stop here!
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
        
        if not sentences:
            return ["No valid sentences found in the provided text."]
            
        return sentences

    except Exception as e:
        # Raising an exception here tells the agent the tool FAILED, 
        # so it won't try to use the error message as data.
        raise Exception(f"Linguistic processing failed: {str(e)}")
