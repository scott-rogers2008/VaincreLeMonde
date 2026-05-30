import json
from agents.exploration_agent import DeepSeekR1Agent
from agents.meta_prompter import MetaPromptingAgent

def run_agent_loop(user_objective: str, max_steps: int = 4):
    print(f"🧠 [Initializing DeepSeek R1 Engine for Task]: {user_objective}")
    
    # Initialize our agents
    agent = DeepSeekR1Agent()
    prompter = MetaPromptingAgent()
    
    execution_history = []
    current_step = 1
    success = False
    final_solution = ""
    
    # Track graph context accessed during this run for the escalation agent
    graph_context_log = []

    while current_step <= max_steps:
        print(f"\n🔄 --- STEP {current_step} of {max_steps} ---")
        
        # Format history string for the LLM context window
        history_str = "\n".join(execution_history) if execution_history else "None"
        
        # Execute the step
        step_result = agent.execute_step(user_objective, history_str)
        
        thinking = step_result["thinking"]
        action = step_result["action"]
        
        print(f"🤔 [Thinking]:\n{thinking}\n")
        
        # 1. Handle Successful Completion
        if action.get("status") == "COMPLETE":
            print("✅ Agent reached a definitive conclusion!")
            final_solution = action.get("final_answer", "")
            success = True
            break
            
        # 2. Handle Tool Execution Strategy
        elif action.get("status") == "CONTINUE":
            tool_name = action.get("tool_name")
            tool_arg = action.get("tool_argument")
            print(f"🛠️ [Calling Tool]: {tool_name} with arg: '{tool_arg}'")
            
            # --- HUMAN-IN-THE-LOOP INJECTION ---
            # Press enter to let it run, or type a correction if it uses a tool wrong!
            user_guidance = input("⌨️ [Optional Correction] Press Enter to execute tool, or type guidance to override: ").strip()
            
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
                
            # Log output for both history context and the escalation prompter
            graph_context_log.append(f"Tool Result ({tool_name}):\n{tool_output}")
            execution_history.append(
                f"Step {current_step} Action: Called {tool_name}({tool_arg})\nResult:\n{tool_output}"
            )
            
        # 3. Handle Local Model Extraction Failures
        else:
            print("⚠️ Local model failed to output strict tool JSON format.")
            execution_history.append(f"Step {current_step} Error: Format constraint violation.")
            break
            
        current_step += 1

    # Close database connections safely
    agent.tools.close()

    # Final Evaluation & Escalation Branch
    if success:
        print("\n================ FINAL ANSWER ================")
        print(final_solution)
        print("==============================================")
    else:
        print("\n🚨 Local reasoning limit reached or trapped. Escalating problem context...")
        
        history_payload = "\n\n".join(execution_history)
        context_payload = "\n\n".join(graph_context_log)
        
        # Call the Meta-Prompting Agent to output our diagnostic markdown file
        escalated_prompt = prompter.generate_escalation_prompt(
            failed_task=user_objective,
            loop_history=history_payload,
            graph_context=context_payload
        )
        prompter.export_prompt_to_file(escalated_prompt)

if __name__ == "__main__":
    # Test task statement
    query = "Analyze the method handling codebase indexing and identify where data sync errors occur."
    run_agent_loop(query)
