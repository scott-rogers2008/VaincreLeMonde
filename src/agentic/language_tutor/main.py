from smolagents import LiteLLMModel
from agents.scout import create_scout_agent
from agents.philologist import create_philologist_agent
from agents.codex import create_codex_agent
from agents.librarian import create_librarian_agent
from agents.quality_control import create_quality_control_agent

model = LiteLLMModel(model_id="ollama/qwen3:8b")

philologist = create_philologist_agent(model)
codex = create_codex_agent(model)
scout = create_scout_agent(model)
quality_control = create_quality_control_agent(model, philologist)
librarian = create_librarian_agent(model, scout, codex, quality_control)

MISSION_URL = "https://www.grimmstories.com/de/grimm_maerchen/hansel_und_gretel"
LANGUAGE_ID = "DEU-ZZ-M"

def start_collaborative_session():
    print("--- Language Tutor Collaborative Session ---")
    print("Examples: \n - 'Hansel and Gretel in German from [URL]'\n - 'Shakespeare's Hamlet from [URL]'")
    
    # One flexible input instead of two rigid ones
    user_request = input("\nWhat story and language are we working on today?\n> ")

    # We pass the raw request to the libraian, who will orchastrate the other agetns
    librarian.run(
        f"Process this request: {user_request}.\n "
        "1. Consult 'codex' to identify the language and get the integer ID assiociated with it.\n "
        "2. Scrape the story and clean it of excess html baggage.\n "
        "3. Split the story into sentences.\n "
        "4. Add any new words to the dictionary. "
    )


if __name__ == "__main__":
    start_collaborative_session()

