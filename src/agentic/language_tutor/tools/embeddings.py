# tools/embeddings.py
import ollama
from smolagents import tool

@tool
def get_embeddings(text_input: str | list) -> list:
    """
    Generates BGE-M3 embedding vectors using Ollama.
    Args:
        text_input: A single string or a list of strings to embed.
    """
    try:
        # Handle both single strings and lists
        inputs = [text_input] if isinstance(text_input, str) else text_input
        
        response = ollama.embed(
            model='bge-m3',
            input=inputs
        )
        embeddings = response.get('embeddings', [])
        
        # If the input was a single string, return the single vector
        # If it was a list, return the list of vectors
        return embeddings[0] if isinstance(text_input, str) else embeddings
    except Exception as e:
        raise Exception(f"Embedding generation failed: {str(e)}")
