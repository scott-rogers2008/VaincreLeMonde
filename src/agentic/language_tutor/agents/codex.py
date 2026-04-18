# agents/codex.py
from smolagents import CodeAgent
from tools import get_language_id # Your tool that queries the 'languages' table

def create_codex_agent(model):
    return CodeAgent(
        tools=[get_language_id],
        model=model,
        name="codex",
        description="Specialist in resolving language descriptions into unique id_codes from the database."
    )
