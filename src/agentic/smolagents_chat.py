# src/agentic/smolagents_chat.py

import os
from smolagents import CodeAgent, ToolCallingAgent, LiteLLMModel, LogLevel
from smolagents.memory import TaskStep

# Global Utility Imports
from agentic.codebase_guru.utils import get_git_root

# Import our cleanly separated tools module
import agentic.smolagents_tools as st

BASE_DIR = os.path.abspath(get_git_root(os.curdir))

# Context window configuration restricted to protect 12GB local VRAM ceilings
MODEL_LLM = LiteLLMModel(
    model_id="ollama/llama3.1", 
    api_base="http://localhost:11434",
    num_ctx=8192
)

# ------------------------------------------------------------------------
# 🧠 CORE AGENT SCHEMAS & DELEGATION STRUCTS
# ------------------------------------------------------------------------

agent_codex = ToolCallingAgent(
    tools=[st.get_language_id],
    model=MODEL_LLM,
    name="codex",
    description="Resolves natural language requests into unique language tracking database primary keys.",
    instructions="Consult schema tables to extract language matching constraints."
)

# Universal Main Orchestration Unit - added fetch_chat_history to the toolbelt
universal_agent = CodeAgent(
    tools=[
        st.vector_search, st.search_semantic_code, st.check_documentation_history, 
        st.list_file_contents, st.list_directory, st.read_file, st.db_content_reader,
        st.ask_user_confirmation, st.fetch_chat_history
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
    print(" -> Codebase Queries   : nomic-embed-text (768 Dim Index)")
    print(" -> Multi-lingual Docs : bge-m3 (1024 Dim Index)")
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
