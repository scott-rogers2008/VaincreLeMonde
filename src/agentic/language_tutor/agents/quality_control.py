# agents/quality_control.py

from smolagents import ToolCallingAgent
from tools import get_shared_memory, update_agent_memory, sentence_splitter, get_raw_html
from tools import read_markdown_content, register_work, library_search

def create_quality_control_agent(model, philologist_managed):
    return ToolCallingAgent(
        tools=[ get_shared_memory, update_agent_memory, sentence_splitter, get_raw_html, 
               read_markdown_content, register_work, library_search],
        model=model,
        managed_agents=[philologist_managed],
        name="quality_control",
        description="Simple agent that verifies that the sentences and sources correlate correctly and correctly registered and passed to the philologist."
    )