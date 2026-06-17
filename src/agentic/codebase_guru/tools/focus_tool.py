# src/agentic/codebase_guru/tools/focus_tool.py
import os
from pathlib import Path
from .utils import get_git_root
from .graph_db import CodebaseGraphManager

class LocalFocusTool:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        self.db = CodebaseGraphManager()

    def build_local_context(self, target_path: str, objective: str, fallbacks: list = None) -> str:
        """
        Builds a compact prompt window for local reasoning models,
        safely querying file dependencies out of your FalkorDB container.
        """
        # Clean and normalize paths using Pathlib to eliminate cross-slash mixing
        raw_path = Path(target_path.replace("\\", "/"))
        
        # Strip 'src' if explicitly passed to ensure graph keys align perfectly
        if raw_path.parts and raw_path.parts[0] == "src":
            db_path = str(Path(*raw_path.parts[1:]).as_posix())
        else:
            db_path = str(raw_path.as_posix())

        # Construct absolute disk path natively for standard filesystem operations
        full_disk_path = os.path.normpath(os.path.join(self.git_root, "src", db_path))
        file_exists = os.path.exists(full_disk_path)
        context_lines = []

        if file_exists:
            try:
                with open(full_disk_path, "r", encoding="utf-8", errors="replace") as f:
                    file_body = f.read()
            except Exception as e:
                file_body = f"# Error reading file contents from local storage disk: {e}"
            
            code_block = f"```python\n{file_body}\n```" if db_path.endswith(".py") else f"```text\n{file_body}\n```"
            mode_header = f"[FOCUS TARGET DETECTED: src/{db_path}]"

            # Query FalkorDB cleanly using direct, non-wrapping openCypher
            cypher = "MATCH (f:File {path: $path})-[:CONTAINS]->(m:Method) RETURN m.name AS name"
            try:
                records = self.db.graph.query(cypher, {"path": db_path})
                # FalkorDB returns rows unpacked within record.result_set matrices
                methods = [r[0] for r in records.result_set]
                if methods:
                    context_lines.append(f"Tracked Graph Components: {', '.join(methods)}")
            except Exception as e:
                print(f"⚠️ FalkorDB context fetching skipped for {db_path}: {e}")
        else:
            code_block = "# [File does not exist yet on local disk storage]"
            mode_header = f"[NEW WORKSPACE CREATION BLUEPRINT: src/{db_path}]"
            context_lines.append("Target path is a new module. Pulling structural interface anchors:")
            
            targets = fallbacks if fallbacks else ["agentic/codebase_guru/tools/graph_db.py"]
            for target in targets:
                t_raw = Path(target.replace("\\", "/"))
                t_db = str(Path(*t_raw.parts[1:]).as_posix()) if t_raw.parts and t_raw.parts[0] == "src" else str(t_raw.as_posix())
                
                cypher = "MATCH (f:File {path: $path})-[:CONTAINS]->(m:Method) RETURN m.name AS name"
                try:
                    res = self.db.graph.query(cypher, {"path": t_db})
                    methods = [r[0] for r in res.result_set]
                    if methods:
                        context_lines.append(f" - Interface hooks from src/{t_db}: {', '.join(methods)}")
                except Exception:
                    pass

        context_payload = "\n".join(context_lines) if context_lines else "No direct database dependencies mapped."
        
        return f"""{mode_header}
You are an expert software developer code-generation engine operating locally on hardware context.
Review the file context provided below and solve the user objective.

[DESTINATION TARGET MODULE]
src/{db_path}

[STRUCTURAL CONTEXT & DEPENDENCIES]
{context_payload}

[ACTIVE SOURCE STATE]
{code_block}

[OBJECTIVE]
> {objective}

[CRITICAL INSTRUCTION]
Your response must contain actual code modifications, additions, or full structural updates inside markdown code blocks.
Do not suggest fixes in conversational text. If you can't output valid code blocks to solve this objective, you must fail the step.
"""

    def close(self):
        pass
