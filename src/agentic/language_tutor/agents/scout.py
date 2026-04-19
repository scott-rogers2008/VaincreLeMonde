# agents/scout.py

from smolagents import ToolCallingAgent 
from tools import get_raw_html, process_and_save_document, get_shared_memory, update_agent_memory
from tools import directory_explorer, manage_directory, ask_user_confirmation, read_markdown_content

def create_scout_agent(model):
    return ToolCallingAgent(
        tools=[get_raw_html, process_and_save_document, read_markdown_content,
               directory_explorer, manage_directory, ask_user_confirmation, get_shared_memory, update_agent_memory],
        model=model,
        name="scout",
        description="A specialist that scrapes URLs, manages story files, and triggers philological analysis.",
        instructions=(
            "1. Check if it's already been downloaded for the correct language using the directory_explorer, or if needed Scrape content using get_raw_html.\n "
            "2. RUN directory_explorer to see the current /references/ tree structure.\n "
            "3. Based on the content type, pick the best existing path (e.g., 'speeches/religious/BYU_speeches').\n "
            "4. If no suitable directory exists, use manage_directory(path, create=False).\n "
            "5. STOP and return a summary and proposed path for approval.\n "
            "6. Only after the user gives approval can you create a new path manage_directory(path, create=True).\n "
            "7. Extract scaped text and Save as .md using process_and_save_document.\n "
            "8. RE-READ the saved .md file using read_markdown_content to ensure you have the full text.\n "
            "9. Pass that full text back to the librarian.\n "
        )
    )
