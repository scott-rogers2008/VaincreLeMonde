# src/agentic/language_tutor/tools/embeddings.py
import ollama

def get_embeddings(text_input: str | list) -> list:
    """Generates BGE-M3 embedding vectors using local Ollama endpoints."""
    try:
        inputs = [text_input] if isinstance(text_input, str) else text_input
        response = ollama.embed(
            model='bge-m3',
            input=inputs
        )
        embeddings = response.get('embeddings', [])
        return embeddings[0] if isinstance(text_input, str) else embeddings
    except Exception as e:
        raise Exception(f"Embedding generation failed: {str(e)}")
