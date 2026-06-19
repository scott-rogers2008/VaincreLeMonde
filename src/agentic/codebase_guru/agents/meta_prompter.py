# src/agentic/codebase_guru/agents/meta_prompter.py
import os
from .utils import get_git_root

class AdvancedMetaPrompter:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        # Pure exclusion set matching standard system properties
        self.exclude_dirs = {
            '.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', 
            '.vs', '.angular', '.vscode', 'node_modules', "angular", 
            'dist', 'browser', 'out', 'build', '__pycache__'
        }

    def _analyze_tutor_infrastructure(self) -> dict:
        """Scans the repository using an exclusion list strategy to discover all files."""
        stats = {
            "python_files": 0,
            "typescript_files": 0,
            "total_files": 0,
            "pedagogical_modules": [],
            "goal_setting_modules": []
        }
        
        src_path = os.path.join(self.git_root, "src")
        scan_target = src_path if os.path.exists(src_path) else self.git_root
        
        for root, dirs, files in os.walk(scan_target):
            # Prune exclusions in-place to avoid parsing bloated build/env spaces
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith('.')]
            
            for file in files:
                stats["total_files"] += 1
                rel_file_path = os.path.relpath(os.path.join(root, file), self.git_root)
                clean_path = rel_file_path.replace("\\", "/")
                
                if file.endswith('.py'):
                    stats["python_files"] += 1
                elif file.endswith('.ts') or file.endswith('.tsx'):
                    stats["typescript_files"] += 1
                
                # Broad mapping strategy: All Python/TS modules are captured dynamically
                lower_name = file.lower()
                stats["pedagogical_modules"].append(clean_path)
                
                # If it relates to core framework, matrix mapping, or profile tracks, flag as goal module
                if any(k in lower_name or k in root.lower() for k in ["goal", "metric", "session", "progress", "user", "matrix", "core"]):
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
        """Scans a target area, aggregates files, and splits prompts into safe sizes."""
        stats = self._analyze_tutor_infrastructure()
        full_area_path = os.path.abspath(os.path.join(self.git_root, target_area))
        if not os.path.exists(full_area_path):
            full_area_path = os.path.abspath(os.path.join(self.git_root, "src", target_area))
            if not os.path.exists(full_area_path):
                return ["❌ Error: Could not locate target area or directory."]

        packaged_files = []
        if os.path.isdir(full_area_path):
            for root, dirs, files in os.walk(full_area_path):
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                for file in files:
                    if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                        abs_p = os.path.join(root, file)
                        rel_p = os.path.relpath(abs_p, self.git_root).replace("\\", "/")
                        packaged_files.append((rel_p, self._safe_read_file(rel_p)))
        else:
            rel_p = os.path.relpath(full_area_path, self.git_root).replace("\\", "/")
            packaged_files.append((rel_p, self._safe_read_file(rel_p)))

        drivers = [
            "agentic/codebase_guru/tools/parser.py",
            "agentic/codebase_guru/tools/graph_db.py",
            "agentic/codebase_guru/tools/git_sync.py"
        ]
        
        compiled_drivers = []
        for d_path in drivers:
            content = self._safe_read_file(d_path)
            if "File not found" not in content:
                compiled_drivers.append((d_path, content))

        chunks = []
        chunk_counter = 1

        for rel_p, contents in compiled_drivers:
            # CRITICAL SAFETY UNIFICATION: Injected the core preservation constraints into baseline drivers
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
### ⚡ CRITICAL CODE PRESERVATION CONSTRAINT (IMMUTABLE ANCHORS)
- Every single piece of pre-existing functionality inside this system (including multi-lingual tracking, language_tutor pipelines, and legacy database tools) must be preserved.
- When generating fixes or additions, write your updates on top of the original baseline. Do NOT clear, strip, or replace adjacent system branches out of files.
---
### 🔌 BACKEND SHARED DRIVERS (BATCH)
#### 📂 Driver: `{rel_p}`
```python
{contents}
```
"""
            chunks.append(part_driver)
            chunk_counter += 1

        MAX_CHUNK_CHARS = 7000
        current_chunk_text = ""
        
        for rel_p, contents in packaged_files:
            file_block = f"### 📄 TARGET AREA SOURCE: `{rel_p}`\n```text\n{contents}\n```\n\n"
            if len(current_chunk_text) + len(file_block) > MAX_CHUNK_CHARS and current_chunk_text.strip():
                # CRITICAL SAFETY UNIFICATION: Injected constraints into target file payload headers
                chunk_payload = f"""### 📦 REPOSITORY CONTEXT (PART {chunk_counter})
Here is the next batch of active source files from our target development area. 
Respond with: 'Ingested Part {chunk_counter}, awaiting next payload.'

[PRESERVATION MANDATE]: Retain all original functional modules and logic blocks in this payload chunk.
---
{current_chunk_text}
"""
                chunks.append(chunk_payload)
                chunk_counter += 1
                current_chunk_text = file_block
            else:
                current_chunk_text += file_block

        if current_chunk_text.strip():
            chunk_payload = f"""### 📦 REPOSITORY CONTEXT (PART {chunk_counter} - FINAL)
Here is the final batch of target area files. Please process the system context and generate the required deliverables.

[CRITICAL REMINDER]: Review all preceding multi-part payload contexts. Integrate the final solution with your immutable anchors. Do NOT omit or drop adjacent tool definitions from your output code blocks.
---
{current_chunk_text}
"""
            chunks.append(chunk_payload)

        return chunks

    def export_prompt_to_file(self, prompt_chunks: list, filename_base="refactor_blueprint"):
        for idx, chunk in enumerate(prompt_chunks, 1):
            filename = f"{filename_base}_part{idx}.md"
            output_path = os.path.join(self.git_root, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(chunk)
            print(f"📁 Exported: {filename}")

    def generate_escalation_prompt(self, failed_task: str, loop_history: str, graph_context: str) -> str:
        repo_stats = self._analyze_tutor_infrastructure()
        return f"""### SYSTEM INSTRUCTION
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
### 🗺️ FALKORDB EXTRACTED GRAPH CONTEXT
```text
{graph_context}
```
---
### 📥 EXPECTED ARCHITECTURAL RESPONSE FORMAT
1. **Root Cause Diagnosis**: Detail why the local model failed or where the code paths diverge.
2. **Refactored Code Blueprints**: Provide production-ready, clean, and typed implementations.

3. **CRITICAL CODE PRESERVATION CONSTRAINT**:
   - DO NOT remove or "gut" pre-existing adjacent systems, tools, or functionalities (e.g., if adding a new feature to tutor_engine.py, ensure all language tutor routing, SQL readers, and dual escalation agents remain intact).
   - Integrate new features incrementally on top of the existing baseline rather than wiping and starting fresh.
   - Every existing functional path is considered an immutable anchor unless explicitly told otherwise.

4. **FalkorDB openCypher Adjustments**: Provide the exact openCypher updates casting multi-dimensional vector arrays natively using vecf32($vector) to patch fingerprints and documentation history layers cleanly.
"""


