# agents/quality_control.py

from smolagents import ToolCallingAgent, LogLevel
from tools import get_shared_memory, update_agent_memory, db_content_reader, loader
from tools import read_markdown_content, register_work, library_search

def create_quality_control_agent(model, philologist_managed):
    return ToolCallingAgent(
        tools=[ get_shared_memory, update_agent_memory, loader, read_markdown_content,
                register_work, library_search, db_content_reader],
        model=model,
        managed_agents=[philologist_managed],
        name="quality_control",
        description="Simple agent that verifies that the sentences and sources correlate correctly and correctly registered and passed to the philologist.",
        instructions=(
            "1. READ the local version from file using read_markdown_content and split into sentences using sentence_splitter.\n "
            "2. REGISTER work using register_work.\n"
            "2. LOAD the text into the database using loader.\n"
        ),
        verbosity_level=LogLevel.DEBUG,  # FULL VERBOSE
        stream_outputs=True
    )