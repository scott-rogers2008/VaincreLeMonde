from smolagents import CodeAgent
from tools import web_scraper, sentence_splitter

# agents/scout.py

def create_scout_agent(model):
    return CodeAgent(
        tools=[web_scraper, sentence_splitter], # Only the "harvesting" tools
        model=model,
        name="scout",
        description="A specialist that scrapes URLs and splits text into an ordered list of sentences."
    )
