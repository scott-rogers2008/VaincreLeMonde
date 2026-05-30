import os

class MetaPromptingAgent:
    def __init__(self):
        pass

    def generate_escalation_prompt(self, failed_task: str, loop_history: str, graph_context: str) -> str:
        """
        Generates an optimal markdown prompt to feed a larger frontier model
        when your local 14B model reaches its limits.
        """
        escalation_prompt = f"""### SYSTEM INSTRUCTION
You are an expert software engineer and AI architect. A local, self-aware agent tracking code relationships via a Neo4j vector graph has encountered an optimization limit or a reasoning trap while executing a task. 

Your objective is to ingest the repository context, analyze the local agent's failed attempt history, diagnose the root issue, and provide a definitive architectural resolution.

---

### 1. THE TASK ATTEMPTED
> {failed_task}

---

### 2. LOCAL AGENT WORKLOG & THINKING TRAIL
Below is the execution transcript, including the local DeepSeek R1 model's internal thinking logs and structural tools called:

```text
{loop_history}
```

---

### 3. LIVE CODEBASE SUB-GRAPH CONTEXT
This context was pulled dynamically from our Neo4j instance, containing the active function definitions, file mappings, and documentation strings related to the target surface area:

```text
{graph_context}
```

---

### 4. EXPECTED OUTPUT DELIVERABLES
Please process the above information and output a comprehensive solution matching these specifications:
1. **Root Cause Analysis**: Diagnose exactly where the execution logic or documentation intent diverged.
2. **Refactored Implementations**: Provide production-ready, clean code blocks resolving the objective.
3. **Graph State Payload**: Provide a Cypher update command or explicit instructions on how to patch our Neo4j graph nodes if documentation or code bodies have drifted.
"""
        return escalation_prompt

    def export_prompt_to_file(self, prompt_content: str, filename="escalated_prompt.md"):
        """Saves the output to a markdown file for easy copying/pasting."""
        output_path = os.path.join(os.getcwd(), filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)
        print(f"📁 Escalation prompt exported successfully to: {output_path}")
