# agents/librarian.py

from smolagents import ToolCallingAgent
from tools import db_content_loader, db_content_reader, register_work, get_shared_memory, update_agent_memory
from tools import library_search, directory_explorer, ask_user_confirmation, sentence_splitter

def create_librarian_agent(model, scout_managed, codex_managed, quality_control):
    return ToolCallingAgent(
        tools=[library_search, register_work, db_content_loader, get_shared_memory, update_agent_memory,
                db_content_reader, directory_explorer, ask_user_confirmation, sentence_splitter], 
        model=model,
        managed_agents=[scout_managed, codex_managed, quality_control],
        instructions=(
            "You are the Librarian. You manage the language library.\n"
            "1. Use 'codex' to resolve language names to IDs.\n "
            "2. Use 'library_search' to see if we already have the story.\n "
            "3. If missing, tell 'scout' to find the story and pass back the full text and local path.\n "
            "4. Register the work including the url and local path.\n "
            "5. Parse the text into sentences using 'quality_control' which will pass each sentence to the philologist."
        )
    )
