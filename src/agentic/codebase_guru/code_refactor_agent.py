# src/agentic/codebase_guru/code_refactor_agent.py
import os
import re
import sys
from .agents.exploration_agent import DeepSeekR1Agent
from .agents.meta_prompter import AdvancedMetaPrompter

def contains_valid_code_block(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"```(?:python|ts|tsx|js|jsx|json)", text))

def run_agent_loop(user_objective: str, target_area: str = None, max_steps: int = 4) -> str:
    """
    Executes a systemic refactoring pass. 
    Returns the final answer or an error message to the calling process.
    """
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
        raw_content = step_result.get("content", "")
        action = step_result.get("action", {})
        
        if contains_valid_code_block(raw_content) or contains_valid_code_block(str(action)):
            return raw_content if raw_content else str(action)

    # 🧠 MODE 2: STANDARD EXPLORATION LOOP
    agent = DeepSeekR1Agent()
    execution_history = []
    seen_tool_arguments = set()
    current_step = 1
    
    while current_step <= max_steps:
        history_str = "\n".join(execution_history) if execution_history else "None"
        step_result = agent.execute_step(user_objective, history_str)
        action = step_result.get("action", {})
        
        if not isinstance(action, dict) or not action:
            break
            
        if action.get("status") == "COMPLETE":
            agent.tools.close()
            return action.get("final_answer", "Refactoring loop complete.")
            
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
                
            execution_history.append(f"Step {current_step} Action: {tool_name}({tool_arg})\nResult:\n{tool_output}")
        current_step += 1
        
    agent.tools.close()
    return "Refactoring escalation payload exported. Check root directory workspace structures."

if __name__ == "__main__":
    goal = os.environ.get("INTEGRATION_GOAL", "Review suite and unify codebase.")
    area = os.environ.get("AREA_TO_IMPROVE", "agentic")
    out = run_agent_loop(user_objective=goal, target_area=area)
    print(out)
