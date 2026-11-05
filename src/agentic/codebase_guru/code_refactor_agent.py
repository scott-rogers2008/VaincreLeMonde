# src/agentic/codebase_guru/code_refactor_agent.py
import os
import re
import sys
import subprocess
import logging
from .agents.exploration_agent import DeepSeekR1Agent
from .agents.meta_prompter import AdvancedMetaPrompter

logger = logging.getLogger(__name__)

def contains_valid_code_block(text: str) -> bool:
    if not text:
        return False
    # Explicitly recognizes html and css alongside standard programming languages
    return bool(re.search(r"```(?:python|ts|tsx|js|jsx|json|html|css)", text))

def execute_repository_git_sync() -> bool:
    """
    Spawns a subprocess to execute git_sync.py at the workspace root area
    to ensure all local tracking metrics and graph hashes are synchronized.
    """
    print("🔄 [State Engine Sync]: Executing repository git_sync.py synchronization pass...")
    try:
        # Determine the project directory root path relative to this script location
        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../../"))
        sync_script_path = os.path.join(base_dir, "git_sync.py")
        
        if not os.path.exists(sync_script_path):
            # Fallback check for alternate script paths in nested directories
            sync_script_path = os.path.join(base_dir, "src", "git_sync.py")

        if not os.path.exists(sync_script_path):
            print("⚠️ [Sync Warning]: git_sync.py script node not detected at root hooks. Proceeding with static disk state.")
            return False

        # Run via the active environment interpreter process handle
        cmd = [sys.executable, sync_script_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print("✨ [Sync Success]: Codebase graph hashes committed atomically to active registries.")
            return True
        else:
            print(f"❌ [Sync Warning Failure]: git_sync.py exited with non-zero status code: {result.returncode}")
            print(f"Standard Error Log Output:\n{result.stderr}")
            return False
            
    except Exception as e:
        print(f"⚠️ [Sync Interrupted]: Subprocess tracking exception logged: {str(e)}")
        return False

def run_agent_loop(user_objective: str, target_area: str = None, max_steps: int = 4) -> str:
    """
    Executes a systemic refactoring pass. Automatically runs git_sync beforehand
    to prevent stale filesystem footprints from confusing context models.
    """
    # 🔒 SECURE AUTOMATED GATEWAY: Sync repository metrics prior to building prompt layers
    execute_repository_git_sync()

    prompter = AdvancedMetaPrompter()
    
    # 🎯 MODE 1: TARGETED AREA INTERCEPT
    if target_area:
        from .tools.focus_tool import LocalFocusTool
        focus_tool = LocalFocusTool()
        suggested_fallbacks = ["agentic/codebase_guru/tools/graph_db.py", "agentic/codebase_guru/tools/agent_tools.py"]
        
        focused_local_prompt = focus_tool.build_local_context(
            target_path=target_area,
            objective=user_objective,
            fallbacks=suggested_fallbacks
        )
        focus_tool.close()
        
        agent = DeepSeekR1Agent()
        step_result = agent.execute_step(focused_local_prompt)
        thinking = step_result.get("thinking", "")
        raw_content = step_result.get("content", "")
        action = step_result.get("action", {})

        if thinking:
            print(f"🤔 [Local Thinking Trace]:\n{thinking}\n")
        
        is_complete = action.get("status") == "COMPLETE" if isinstance(action, dict) else False
        has_code = contains_valid_code_block(raw_content) or contains_valid_code_block(str(action))

        if is_complete or has_code:
            print(f"✨ [Local Focus Success!]: Content successfully generated inside parameters.")
            return raw_content if raw_content else str(action)

        print("\n🚨 [Local Loop Overwhelmed or Format Failed]: Escalating context immediately...")
        print("⏳ Running original AdvancedMetaPrompter payload chunking pipelines...")
        
        prompter = AdvancedMetaPrompter()
        refactor_chunks = prompter.generate_refactoring_prompt(
            target_area=target_area,
            improvement_goal=user_objective
        )
        
        if refactor_chunks and str(refactor_chunks[0]).startswith("❌"):
            print(refactor_chunks[0])
        else:
            prompter.export_prompt_to_file(refactor_chunks)
            print(f"✨ Fallback complete! Context split into {len(refactor_chunks)} parts to prevent server size drops.")
            print("⚠️ Local GPU execution suspended. Ready for sequential copy-pasting to a larger LLM.")
        return
    

    # 🧠 MODE 2: STANDARD EXPLORATION LOOP
    agent = DeepSeekR1Agent()
    execution_history = []
    graph_context_log = []
    seen_tool_arguments = set()
    current_step = 1
    final_solution = ""
    success = False
    
    while current_step <= max_steps:
        history_str = "\n".join(execution_history) if execution_history else "None"
        step_result = agent.execute_step(user_objective, history_str)
        action = step_result.get("action", {})
        
        if not isinstance(action, dict) or not action:
            break
            
        if action.get("status") == "COMPLETE":
            agent.tools.close()
            success = True
            final_solution = action.get("final_answer", "Refactoring loop complete.")
            break
            
        elif action.get("status") == "CONTINUE":
            tool_name = action.get("tool_name")
            tool_arg = action.get("tool_argument", "").strip()
            loop_fingerprint = f"{tool_name}:{tool_arg}"
            
            if loop_fingerprint in seen_tool_arguments:
                break
            seen_tool_arguments.add(loop_fingerprint)
            
            if tool_name == "search_semantic_code":
                tool_output = agent.tools.search_semantic_code(tool_arg)
            elif tool_name == "check_documentation_history":
                tool_output = agent.tools.check_documentation_history(tool_arg)
            elif tool_name == "list_file_contents":
                tool_output = agent.tools.list_file_contents(tool_arg)
            else:
                tool_output = f"Error: Tool '{tool_name}' not found."
                
            graph_context_log.append(f"Tool Result ({tool_name}):\n{tool_output}")
            execution_history.append(f"Step {current_step} Action: {tool_name}({tool_arg})\nResult:\n{tool_output}")

        else:
            print("⚠️ Local model failed to output strict tool JSON format.")
            execution_history.append(f"Step {current_step} Error: Format constraint violation.")
            break

        current_step += 1
        
    agent.tools.close()

    if success:
        print("\n================ FINAL ANSWER ================")
        print(final_solution)
        print("==============================================")
    else:
        print("\n🚨 Local reasoning limit reached or trapped. Escalating problem context...")
        history_payload = "\n\n".join(execution_history)
        context_payload = "\n\n".join(graph_context_log)
        
        escalated_prompt = prompter.generate_escalation_prompt(
            failed_task=user_objective,
            loop_history=history_payload,
            graph_context=context_payload
        )
        prompter.export_prompt_to_file(escalated_prompt, filename="escalated_prompt.md")

if __name__ == "__main__":
    goal = os.environ.get("INTEGRATION_GOAL", "Improve study-dashboard to create a quiz based on selected materials.")
    area = os.environ.get("AREA_TO_IMPROVE", "src")
    out = run_agent_loop(user_objective=goal, target_area=area)
    print(out)
