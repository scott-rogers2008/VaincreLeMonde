# agents/librarian.py

from smolagents import ToolCallingAgent, LogLevel
from tools import db_content_reader, register_work, get_shared_memory, update_agent_memory
from tools import library_search, ask_user_confirmation, loader

def create_librarian_agent(model, scout_managed, codex_managed, quality_control):
    return ToolCallingAgent(
        tools=[library_search, register_work, get_shared_memory, update_agent_memory,
                db_content_reader, ask_user_confirmation, loader], 
        model=model,
        managed_agents=[scout_managed, codex_managed, quality_control],
        instructions=(
            "You are the Librarian. You manage the language library.\n"
            "1. Use 'codex' to resolve language names to IDs.\n "
            "2. Use 'library_search' to see if we already have the story.\n "
            "3. If missing, tell 'scout' to find the story and pass back the full text and local path.\n "
            "4. Register the work including the url and local path.\n "
            "5. Load full text using loader."
            "FINAL STEP: have 'quality_control' verify that all sentences are loaded properly."
        ),
        verbosity_level=LogLevel.DEBUG,  # FULL VERBOSE
        stream_outputs=True
    )
