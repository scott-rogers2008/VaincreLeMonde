from smolagents import tool
from sqlalchemy import text
from .database_manager import engine

@tool
def register_work(title: str, lang_id: int, work_type: str, source_url: str, path: str, author: str = None, parent_id: int = None) -> str:
    """
    Creates a new entry in 'literary_works' and returns the new Work ID.
    Args:
        title: The name of the story, book, or chapter.
        lang_id: The integer ID from the language table.
        work_type: Must be 'SERIES', 'BOOK', 'CHAPTER', or 'SHORT_STORY'.
        author: Optional name of the author.
        parent_id: Optional ID of the parent work (e.g., the Book ID if this is a Chapter).
        source_url: url of source from which the text came from
        path: local path of text in references
    """
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO literary_works (title, language_id, work_type, author, parent_id, source_url, local_path)
                VALUES (:title, :lang, :type, :author, :parent, :url, :path)
                RETURNING id;
            """)
            result = conn.execute(query, {
                "title": title, "lang": lang_id, "type": work_type.upper(), 
                "author": author, "parent": parent_id, "url": source_url, "path": path
            })
            new_id = result.fetchone()[0]
            conn.commit()
            return f"Success: Work '{title}' registered with ID: {new_id}"
    except Exception as e:
        return f"Database Error: {str(e)}"

@tool
def library_search(search_term: str) -> list:
    """
    Searches the 'literary_works' table by title or author.
    Args:
        search_term: Part of a title or author name to look for.
    """
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, title, author, work_type, language_id, source_url, local_path 
                FROM literary_works 
                WHERE title ILIKE :term OR author ILIKE :term
            """)
            results = conn.execute(query, {"term": f"%{search_term}%"}).fetchall()
            return [dict(row._mapping) for row in results]
    except Exception as e:
        return [f"Error: {str(e)}"]
