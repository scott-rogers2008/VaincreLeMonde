from smolagents import CodeAgent
from tools import db_content_loader, db_content_reader, register_work, library_search

def create_librarian_agent(model, scout_managed, codex_managed, philologist_managed):
    return CodeAgent(
        tools=[library_search, register_work, db_content_loader, db_content_reader], 
        model=model,
        managed_agents=[scout_managed, codex_managed, philologist_managed],
        instructions=(
            "You are the Librarian. You manage the language library.\n"
            "1. Use 'codex' to resolve language names to IDs.\n"
            "2. Use 'library_search' to see if we already have the story.\n"
            "3. If missing, tell 'scout' to scrape the URL and return sentences.\n"
            "4. Get user approval for the summary provided by scout.\n"
            "5. Register the work, then use 'db_content_loader' to save the Scout's sentences.\n"
            "6. Send the work_id to 'philologist' for analysis."
        )
    )