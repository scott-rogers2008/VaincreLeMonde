# src/agentic/codebase_guru/run_agent.py

import os
from agents.exploration_agent import DeepSeekR1Agent
from agents.meta_prompter import AdvancedMetaPrompter

def run_agent_loop(user_objective: str, target_area: str = None, max_steps: int = 4):
    """
    Executes a reasoning pass.
    Features a low-resource CPU-only intercept for targeted directory refactoring,
    and automatic algorithmic loop-guardrails for standard exploration tasks.
    """
    prompter = AdvancedMetaPrompter()
    
    # ------------------------------------------------------------------------
    # 🎯 MODE 1: TARGETED AREA/DIRECTORY INTERCEPT (LOW-RESOURCE CPU LOOP)
    # ------------------------------------------------------------------------
    if target_area:
        print(f"🛠️ [Targeted Improvement Mode] Packaging context area: {target_area}")
        print("⏳ Extracting source files and compiling engineering specifications...")
        
        # Generates a list of safely-sized prompt strings
        refactor_chunks = prompter.generate_refactoring_prompt(
            target_area=target_area,
            improvement_goal=user_objective
        )
        
        if refactor_chunks and str(refactor_chunks[0]).startswith("❌"):
            print(refactor_chunks[0])
        else:
            # Writes out separate files (refactor_blueprint_part1.md, part2.md, etc.)
            prompter.export_prompt_to_file(refactor_chunks)
            print(f"✨ Success! Context split into {len(refactor_chunks)} parts to prevent server size drops.")
            print("🛑 GPU Bypassed. Ready for sequential copy-pasting.")
        return

    # ------------------------------------------------------------------------
    # 🧠 MODE 2: STANDARD CODEBASE EXPLORATION LOOP (LOCAL LLM AUTOMATION)
    # ------------------------------------------------------------------------
    print(f"🧠 [Initializing DeepSeek R1 Engine for Task]: {user_objective}")
    agent = DeepSeekR1Agent()
    execution_history = []
    graph_context_log = []
    current_step = 1
    success = False
    final_solution = ""

    # Loop Guard: Track past tool arguments to catch infinite overthinking spins
    seen_tool_arguments = set()

    while current_step <= max_steps:
        print(f"\n🔄 --- STEP {current_step} of {max_steps} ---")
        history_str = "\n".join(execution_history) if execution_history else "None"
        
        # Execute local token pass
        step_result = agent.execute_step(user_objective, history_str)
        thinking = step_result.get("thinking", "")
        action = step_result.get("action", {})
        
        if thinking:
            print(f"🤔 [Thinking]:\n{thinking}\n")
        
        # 1. Handle Successful Conclusion
        if action.get("status") == "COMPLETE":
            print("✅ Agent reached a definitive conclusion!")
            final_solution = action.get("final_answer", "")
            success = True
            break
            
        # 2. Handle Tool Execution Strategy
        elif action.get("status") == "CONTINUE":
            tool_name = action.get("tool_name")
            tool_arg = action.get("tool_argument", "").strip()
            
            # Create a unique fingerprint hash matching tool name and argument text
            loop_fingerprint = f"{tool_name}:{tool_arg}"
            
            # LOOP GUARD CHECKPOINT: If the model repeats itself, force a circuit break
            if loop_fingerprint in seen_tool_arguments:
                print(f"🚨 [Loop Guard Triggered]: Agent is spinning on tool query '{loop_fingerprint}'!")
                print("🛑 Forcing an automatic system escalation to protect local GPU resources...")
                execution_history.append(f"Step {current_step} Block: Guardrail cut off repetitive execution of tool parameter '{tool_arg}'.")
                break
                
            seen_tool_arguments.add(loop_fingerprint)
            print(f"🛠️ [Calling Tool]: {tool_name} with arg: '{tool_arg}'")
            
            # Human-in-the-loop interaction window
            user_guidance = input("⌨️ [Optional Correction] Press Enter to run tool, or type guidance to override: ").strip()
            
            if user_guidance:
                print(f"🔄 Intercepting loop! Feeding guidance back to DeepSeek...")
                tool_output = f"User Intervened and provided guidance: {user_guidance}"
            else:
                tool_output = ""
                if tool_name == "search_semantic_code":
                    tool_output = agent.tools.search_semantic_code(tool_arg)
                elif tool_name == "check_documentation_history":
                    tool_output = agent.tools.check_documentation_history(tool_arg)
                elif tool_name == "list_file_contents":
                    tool_output = agent.tools.list_file_contents(tool_arg)
                else:
                    tool_output = f"Error: Tool '{tool_name}' is not recognized."
                    
            graph_context_log.append(f"Tool Result ({tool_name}):\n{tool_output}")
            execution_history.append(f"Step {current_step} Action: Called {tool_name}({tool_arg})\nResult:\n{tool_output}")
            
        # 3. Handle Parsing Failures
        else:
            print("⚠️ Local model failed to output strict tool JSON format.")
            execution_history.append(f"Step {current_step} Error: Format constraint violation.")
            break
            
        current_step += 1

    # Safe closing checkpoint for database drivers
    agent.tools.close()

    # ------------------------------------------------------------------------
    # 📁 ESCALATION LAYER (RUNS AUTOMATICALLY IF COGNITIVE LIMITS ARE HIT)
    # ------------------------------------------------------------------------
    if success:
        print("\n================ FINAL ANSWER ================")
        print(final_solution)
        print("==============================================")
    else:
        print("\n🚨 Local reasoning limit reached or trapped. Escalating problem context...")
        history_payload = "\n\n".join(execution_history)
        context_payload = "\n\n".join(graph_context_log)
        
        # Package history logs along with your multi-language context blueprints
        escalated_prompt = prompter.generate_escalation_prompt(
            failed_task=user_objective,
            loop_history=history_payload,
            graph_context=context_payload
        )
        prompter.export_prompt_to_file(escalated_prompt, filename="escalated_prompt.md")

if __name__ == "__main__":
    # --- CONFIGURE AREA MODE CONTROLS HERE ---
    # Set AREA_TO_IMPROVE to None to run standard codebase exploration.
    # Set AREA_TO_IMPROVE to a directory path to bundle an entire folder instantly!
    
    AREA_TO_IMPROVE = "agentic"  # Target an entire folder
    INTEGRATION_GOAL = "Review suite and unify codebase."
    
    run_agent_loop(user_objective=INTEGRATION_GOAL, target_area=AREA_TO_IMPROVE)
