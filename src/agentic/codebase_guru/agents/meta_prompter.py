# src/agentic/codebase_guru/agents/meta_prompter.py

import os
from .utils import get_git_root

class AdvancedMetaPrompter:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))

    def _analyze_tutor_infrastructure(self) -> dict:
        """Scans the repository to map out code elements handling human education mechanics."""
        stats = {
            "python_files": 0, "typescript_files": 0, "total_files": 0,
            "pedagogical_modules": [], "goal_setting_modules": []
        }
        src_path = os.path.join(self.git_root, "src")
        scan_target = src_path if os.path.exists(src_path) else self.git_root
        
        for root, _, files in os.walk(scan_target):
            for file in files:
                stats["total_files"] += 1
                rel_file_path = os.path.relpath(os.path.join(root, file), self.git_root)
                clean_path = rel_file_path.replace("\\", "/")
                
                if file.endswith('.py'):
                    stats["python_files"] += 1
                elif file.endswith('.ts') or file.endswith('.tsx'):
                    stats["typescript_files"] += 1
                
                lower_name = file.lower()
                if any(k in lower_name for k in ["tutor", "learn", "spaced", "bge", "language", "sync"]):
                    stats["pedagogical_modules"].append(clean_path)
                if any(k in lower_name for k in ["goal", "metric", "session", "progress", "user"]):
                    stats["goal_setting_modules"].append(clean_path)
                    
        return stats

    def _safe_read_file(self, relative_path: str) -> str:
        """Safely reads file strings handling potential cross-OS encodings."""
        full_path = os.path.abspath(os.path.join(self.git_root, relative_path))
        if not os.path.exists(full_path):
            full_path = os.path.abspath(os.path.join(self.git_root, "src", relative_path))
            if not os.path.exists(full_path):
                return f"// File not found on local disk storage: {relative_path}"
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(full_path, "r", encoding="cp1252", errors="replace") as f:
                return f.read()
        except Exception as e:
            return f"// Error extracting file block context: {e}"

    def generate_refactoring_prompt(self, target_area: str, improvement_goal: str) -> list:
        """
        Scans a target area, aggregates files, and splits the engineering prompt 
        into safely-sized context chunks to prevent 'Request Too Large' errors.
        """
        stats = self._analyze_tutor_infrastructure()
        full_area_path = os.path.abspath(os.path.join(self.git_root, target_area))
        
        if not os.path.exists(full_area_path):
            full_area_path = os.path.abspath(os.path.join(self.git_root, "src", target_area))
        if not os.path.exists(full_area_path):
            return ["❌ Error: Could not locate target area or directory."]

        # Gather target codebase files
        packaged_files = []
        if os.path.isdir(full_area_path):
            for root, _, files in os.walk(full_area_path):
                for file in files:
                    if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                        abs_p = os.path.join(root, file)
                        rel_p = os.path.relpath(abs_p, self.git_root).replace("\\", "/")
                        packaged_files.append((rel_p, self._safe_read_file(rel_p)))
        else:
            rel_p = os.path.relpath(full_area_path, self.git_root).replace("\\", "/")
            packaged_files.append((rel_p, self._safe_read_file(rel_p)))

        # Read backend drivers as tuples for granular chunking
        drivers = [
            ("agentic/codebase_guru/tools/parser.py", self._safe_read_file("agentic/codebase_guru/tools/parser.py")),
            ("agentic/codebase_guru/tools/graph_db.py", self._safe_read_file("agentic/codebase_guru/tools/graph_db.py")),
            ("agentic/codebase_guru/tools/git_sync.py", self._safe_read_file("agentic/codebase_guru/tools/git_sync.py"))
        ]

        chunks = []
        chunk_counter = 1

        # --------------------------------------------------------------------
        # 📦 BUILD BASELINE INFRASTRUCTURE CHUNKS (Drivers are split safely)
        # --------------------------------------------------------------------
        current_driver_text = ""
        drivers_in_chunk = 0
        
        for rel_p, contents in drivers:
            # Skip appending if file wasn't found or is empty to save space
            if "File not found" in contents:
                continue
            
            current_driver_text += f"#### 📂 Driver: `{rel_p}`\n```python\n{contents}\n```\n\n"
            drivers_in_chunk += 1
            
            # Split drivers if they are large (Max 1 major tool driver per chunk)
            if drivers_in_chunk >= 1:
                part_driver = f"""### 🎓 SYSTEM INSTRUCTION (PART {chunk_counter} OF MULTI-PART CONTEXT)
You are a Principal AI Learning Architect. We are expanding our complex multi-language Agentic Tutor System.
DO NOT generate code yet. Acknowledge receipt of Part {chunk_counter} and wait for the remaining payload.

---
### 📊 ENVIRONMENT PROFILE
* Target Area: `{target_area}`
* Total Files: {stats['total_files']} ({stats['python_files']} Python, {stats['typescript_files']} TypeScript)

---
### 🎯 INTEGRATION OBJECTIVE
> {improvement_goal}

---
### 🔌 BACKEND SHARED DRIVERS (BATCH)
{current_driver_text}
"""
                chunks.append(part_driver)
                chunk_counter += 1
                current_driver_text = ""
                drivers_in_chunk = 0

        # Catch remaining driver if any
        if current_driver_text:
            part_driver = f"""### 🎓 SYSTEM INSTRUCTION (PART {chunk_counter} OF MULTI-PART CONTEXT)\n{current_driver_text}"""
            chunks.append(part_driver)
            chunk_counter += 1

        # --------------------------------------------------------------------
        # 📦 BUILD TARGET AREA FILE CHUNKS (Max 2 files per message chunk)
        # --------------------------------------------------------------------
        MAX_CHUNK_CHARS = 7000
        current_chunk_text = ""
        files_in_current_chunk = 0

        for rel_p, contents in packaged_files:
            file_block = f"### 📄 TARGET AREA SOURCE: `{rel_p}`\n```text\n{contents}\n```\n\n"
            current_chunk_text += file_block
            files_in_current_chunk += 1

            if len(current_chunk_text) + len(file_block) > MAX_CHUNK_CHARS and current_chunk_text.strip():
                chunk_payload = f"""### 📦 REPOSITORY CONTEXT (PART {chunk_counter})
Here is the next batch of active source files from our target development area. 
Respond with: 'Ingested Part {chunk_counter}, awaiting next payload.'

---
{current_chunk_text}
"""
                chunks.append(chunk_payload)
                chunk_counter += 1
                current_chunk_text = ""
                files_in_current_chunk = 0

        # Catch any trailing files left over
        if current_chunk_text.strip():
            chunk_payload = f"""### 📦 REPOSITORY CONTEXT (PART {chunk_counter} - FINAL)
Here is the final batch of target area files. Please process the system context and generate the required deliverables.

---
{current_chunk_text}
"""
            chunks.append(chunk_payload)

        return chunks

    def export_prompt_to_file(self, prompt_chunks: list, filename_base="refactor_blueprint"):
        """Saves chunks into separate files so you can copy/paste them sequentially."""
        for idx, chunk in enumerate(prompt_chunks, 1):
            filename = f"{filename_base}_part{idx}.md"
            output_path = os.path.join(self.git_root, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(chunk)
            print(f"📁 Exported: {filename}")

    def generate_escalation_prompt(self, failed_task: str, loop_history: str, graph_context: str) -> str:
        """Creates a high-density markdown prompt when the local agent loop fails or traps."""
        repo_stats = self._analyze_tutor_infrastructure()
        
        prompt = f"""### SYSTEM INSTRUCTION
You are an Elite AI Software Architect specializing in mixed-language system integration (Python and TypeScript).
A local code-exploration agent running a 14B model encountered a reasoning trap or context ceiling.

Your goal is to inspect the execution logs, resolve code discrepancies, and provide a definitive architectural resolution.

---
### 📊 REPOSITORY PROFILE
* **Total Tracked Files**: {repo_stats['total_files']} ({repo_stats['python_files']} Python, {repo_stats['typescript_files']} TypeScript)

---
### 🎯 MISSION OBJECTIVE
> {failed_task}

---
### 🕵️ LOCAL AGENT EXECUTION LOGS
```text
{loop_history}
```

---
### 🗺️ NEO4J EXTRACTED GRAPH CONTEXT
```text
{graph_context}
```

---
### 📥 EXPECTED ARCHITECTURAL RESPONSE FORMAT
1. **Root Cause Diagnosis**: Detail why the local model failed or where the code paths diverge.
2. **Refactored Code Blueprints**: Provide production-ready, clean, and typed implementations.
3. **Neo4j Cypher Adjustments**: Provide the exact Neo4j Cypher updates to patch hashes and documentation history.
"""
        return prompt

