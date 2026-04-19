# agents/codex.py

from smolagents import ToolCallingAgent
from tools import get_language_id, ask_user_confirmation, get_shared_memory, update_agent_memory

def create_codex_agent(model):
    return ToolCallingAgent(
        tools=[get_language_id, ask_user_confirmation, get_shared_memory, update_agent_memory],
        model=model,
        name="codex",
        description="Your a language specialist helping a tutor in resolving language descriptions into a unique ID from the database.",
        instructions="""
        The language table has 6 columns:  id | iso_639_1 | name_native | name_english | iso_639_3 | spacy_model.
        The integer id is the unique identifier needed for the database tools to identify the correct language.
        """
    )
