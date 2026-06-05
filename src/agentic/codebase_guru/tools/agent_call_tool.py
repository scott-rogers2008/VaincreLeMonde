# src/agentic/codebase_guru/tools/agent_call_tool.py
import os
import subprocess
from smolagents import tool
from ..utils import get_git_root

@tool
def delegate_to_codebase_guru(user_objective: str, target_area: str = None) -> str:
    """
    Delegates complex codebase exploration, refactoring, or greenfield creations 
    to the deep reasoning loop. Automatically triggers local context filtering 
    and handles multi-part prompt file generation if the task is too large.

    Args:
        user_objective: The specific engineering objective or fix requested.
        target_area: Optional path to a file or directory to focus the analysis on.
    """
    git_root = get_git_root(os.curdir)
    
    # Formulate command arguments to invoke run_agent safely in its own sub-shell
    cmd = ["python", "-m", "agentic.codebase_guru.run_agent"]
    
    # Pass arguments using a standard environment contract to bypass CLI escaping issues
    env_context = os.environ.copy()
    env_context["INTEGRATION_GOAL"] = user_objective
    if target_area:
        env_context["AREA_TO_IMPROVE"] = target_area

    try:
        print(f"\n⚡ [VRAM Swap Request]: Offloading focus session to Codebase Guru...")
        print(f"   Target Scope: '{target_area or 'Global Codebase Search'}'")
        
        # Subprocess isolates the execution pass, allowing Ollama to free up memory cleanly
        result = subprocess.run(
            cmd,
            cwd=git_root,
            env=env_context,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"🚨 Engine Execution Interrupted: {e.stderr}\nOutput Context:\n{e.stdout}"
    except Exception as e:
        return f"🚨 System Interface Exception: {str(e)}"
