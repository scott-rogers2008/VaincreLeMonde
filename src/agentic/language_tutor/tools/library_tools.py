# src/agentic/language_tutor/tools/library_tools.py
from sqlalchemy import text
from .database_manager import engine

def register_work(title: str, lang_id: int, work_type: str, source_url: str, path: str, author: str = None, parent_id: int = None) -> str:
    """Creates a new record entry in the 'literary_works' master relational data table."""
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

def library_search(search_term: str) -> list:
    """Searches active library columns matching explicit string names."""
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
