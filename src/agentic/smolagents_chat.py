# src/agentic/smolagents_chat.py
import os
import json
import re
from smolagents import CodeAgent, ToolCallingAgent, LiteLLMModel, LogLevel, tool
from smolagents.memory import TaskStep

# Global Utility Imports
from utils import get_git_root
import smolagents_tools as st

# 1. Import the REAL codebase tools from your Codebase Guru domain
from codebase_guru.tools.agent_tools import AgentTools
from codebase_guru.tools.agent_call_tool import delegate_to_codebase_guru

# 2. Import the REAL reader and interaction tools from your Language Tutor domain
from language_tutor.tools.database_tools import db_content_reader, get_language_id
from language_tutor.tools.library_tools import library_search
from language_tutor.tools.user_tools import ask_user_confirmation  # <--- FIXED: REAL IMPORT

BASE_DIR = os.path.abspath(get_git_root(os.curdir))

# Context window configuration restricted to protect 12GB local VRAM ceilings
MODEL_LLM = LiteLLMModel(
    model_id="ollama/qwen3.5:9b",
    api_base="http://localhost:11434",
    num_ctx=8192
)

# Instantiate the Codebase Guru tools wrapper
code_tools = AgentTools()

# ------------------------------------------------------------------------
# 🔌 RE-MAP CODEBASE METHODS AS SMOLAGENTS TOOLS
# ------------------------------------------------------------------------

@tool
def search_codebase_semantics(query: str, limit: int = 3) -> str:
    """
    Uses Nomic vector embeddings to search function bodies and class structures inside Neo4j.
    Use this to look up code mechanics, like 'database connection pool' or 'comment parser'.
    Args:
        query: The semantic concept or code feature to search for.
        limit: The maximum number of relevant matching code blocks to return.
    """
    return code_tools.search_semantic_code(user_query=query, limit=limit)

@tool
def check_codebase_documentation_history(method_name: str) -> str:
    """
    Traces the historical timeline of documentation updates for a specific code method 
    inside Neo4j to check for architectural intent shifts or doc drift.
    Args:
        method_name: The single raw name of the function or method to trace.
    """
    return code_tools.check_documentation_history(method_name=method_name)

@tool
def list_tracked_file_methods(file_path: str) -> str:
    """
    Queries Neo4j to list all functions and structural definitions indexed inside a specific file.
    Args:
        file_path: Relative path of the file to list (e.g. 'agentic/codebase_guru/tools/parser.py').
    """
    return code_tools.list_file_contents(file_path=file_path)


# ------------------------------------------------------------------------
# 🧠 CORE AGENT SCHEMAS & DELEGATION STRUCTS
# ------------------------------------------------------------------------

# Dedicated Codex agent using the imported PostgreSQL tool
agent_codex = ToolCallingAgent(
    tools=[get_language_id],
    model=MODEL_LLM,
    name="codex",
    description="Resolves natural language descriptions into unique language database tracking IDs.",
    instructions="Consult the language schema tables via your tool to find matching language database keys."
)

# Universal Main Orchestration Unit - built purely from verified, existing tools
universal_agent = CodeAgent(
    tools=[
        search_codebase_semantics,             # Neo4j Code Vector Search
        check_codebase_documentation_history,  # Neo4j Doc Tracking
        list_tracked_file_methods,             # Neo4j Module Structural Scan
        library_search,                        # PostgreSQL Literary Work Lookups
        db_content_reader,                     # PostgreSQL Chronological Sentence Reads
        delegate_to_codebase_guru,             # VRAM-Safe Subprocess Reasoner (DeepSeek)
        ask_user_confirmation,                 # Human-In-The-Loop Confirmation (From Language Tutor)
        st.fetch_chat_history                  # Long-Term PostgreSQL Memory Retrieval
    ],
    model=MODEL_LLM,
    managed_agents=[agent_codex],
    additional_authorized_imports=["os", "json", "re"],
    verbosity_level=LogLevel.DEBUG
)

# ------------------------------------------------------------------------
# 🚀 PERSISTENT CLI RUNTIME CONTEXT
# ------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n======================================================================")
    print("🎓 UNIVERSAL MULTI-LANGUAGE TUTOR AND CODE ARCHITECT RUNTIME")
    print(f"Directory Anchor: {BASE_DIR}")
    print("Hardware Baseline: RTX 3060 / Context Limit Managed at 8192 Blocks")
    print("Locked Dimension Routing Rules:")
    print(" -> Codebase Queries : Neo4j Graph Network (768 Dim Index)")
    print(" -> Language Content : PostgreSQL Database Tables (1024 Dim Index)")
    print("======================================================================\n")

    # 💾 BOOTSTRAP RESILIENT LONG-TERM MEMORY
    print("🧠 Pulling long-term conversational records from PostgreSQL context...")
    prior_logs = st.fetch_chat_history(num_messages=4)
    if "Database Error" not in prior_logs and "empty" not in prior_logs:
        seed_interaction = TaskStep(task="Review the following chat history log context to ensure continuous session memory.")
        seed_interaction.observations = prior_logs
        universal_agent.memory.steps.append(seed_interaction)
        print("✅ Long-term memory loaded into active agent context workspace.\n")
    else:
        print("💡 No active conversational trace found. Starting clean session matrix.\n")

    while True:
        try:
            user_prompt = input("🚀 UNIVERSAL-TUTOR > ")
            if user_prompt.strip().lower() in ["quit", "exit"]:
                print("Exiting universal runtime loop cleanly.")
                break
            if not user_prompt.strip():
                continue
            if len(user_prompt) > 3000:
                print("⚠️ [VRAM Warning]: Large prompt block detected. Splitting recommended to maintain processing speed.")

            # Run the agent execution layer
            execution_response = universal_agent.run(user_prompt, reset=False)
            print(f"\n✨ [Universal Result]:\n{execution_response}\n")

            # Save the cycle instantly to database tables
            st.save_chat_turn_to_db("user", user_prompt)
            st.save_chat_turn_to_db("ai", str(execution_response))

        except KeyboardInterrupt:
            print("\nSession interrupted via intercept signal.")
            break
        except Exception as e:
            print(f"\n🚨 Loop Processing Fault: {str(e)}\n")
            
    # Clean database teardown on exit
    code_tools.close()
