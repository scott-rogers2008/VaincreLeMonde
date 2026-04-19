from smolagents import tool
from .database_manager import SessionLocal
from sqlalchemy import text

@tool
def update_agent_memory(agent_name: str, key: str, value: str) -> str:
    """
    Saves a specific piece of information to the shared memory table.
    Use this to share data like 'work_id' or 'last_processed_index' between agents.
    
    Args:
        agent_name: The name of the agent saving the info.
        key: The label for the memory (e.g., 'current_work_id').
        value: The value to store (must be a string).
    """
    session = SessionLocal()
    try:
        # Using an UPSERT (Insert or Update) logic
        query = text("""
            INSERT INTO agent_memory (agent_name, memory_key, memory_value, updated_at)
            VALUES (:name, :key, :val, NOW())
            ON CONFLICT (agent_name, memory_key) 
            DO UPDATE SET memory_value = EXCLUDED.memory_value, updated_at = NOW();
        """)
        session.execute(query, {"name": agent_name, "key": key, "val": value})
        session.commit()
        return f"Memory updated: {key} = {value}"
    except Exception as e:
        session.rollback()
        return f"Error updating memory: {str(e)}"
    finally:
        session.close()

@tool
def get_shared_memory(key: str) -> str:
    """
    Retrieves a value from the shared memory table by key. 
    Use this to pick up where another agent left off.
    Args:
        key: the key from which to get the shared memory.
    """
    session = SessionLocal()
    try:
        query = text("SELECT memory_value FROM agent_memory WHERE memory_key = :key ORDER BY updated_at DESC LIMIT 1")
        result = session.execute(query, {"key": key}).fetchone()
        return result[0] if result else "NOT_FOUND"
    finally:
        session.close()
