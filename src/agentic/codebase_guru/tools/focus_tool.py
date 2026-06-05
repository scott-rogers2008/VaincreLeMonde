# src/agentic/codebase_guru/tools/focus_tool.py
import os
from ..utils import get_git_root
from graph_db import CodebaseGraphManager

class LocalFocusTool:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        self.db = CodebaseGraphManager()

    def build_local_context(self, target_path: str, objective: str, fallbacks: list = None) -> str:
        """
        Builds a compact prompt for the local 14B model.
        Reads file text if it exists, or pulls API hooks from Neo4j if it is a new file.
        """
        clean_path = target_path.replace("\\", "/")
        db_path = clean_path[4:] if clean_path.startswith("src/") else clean_path
        
        full_disk_path = os.path.join(self.git_root, target_path if target_path.startswith("src/") else f"src/{target_path}")
        file_exists = os.path.exists(full_disk_path)
        context_lines = []

        if file_exists:
            # Existing File Mode
            try:
                with open(full_disk_path, "r", encoding="utf-8", errors="replace") as f:
                    file_body = f.read()
            except Exception as e:
                file_body = f"# Error reading file: {e}"
            code_block = f"```python\n{file_body}\n```"
            mode_header = f"[FOCUS TARGET DETECTED: src/{db_path}]"
            
            # Tiny verification check from Neo4j
            cypher = "MATCH (f:File {path: $path})-[:CONTAINS]->(m:Method) RETURN m.name AS name"
            with self.db.driver.session() as s:
                records = s.run(cypher, path=db_path)
                methods = [r["name"] for r in records]
                if methods:
                    context_lines.append(f"Tracked Graph Components: {', '.join(methods)}")
        else:
            # New Greenfield Creation Mode
            code_block = "# [File does not exist yet on local disk storage]"
            mode_header = f"[NEW WORKSPACE CREATION BLUEPRINT: src/{db_path}]"
            context_lines.append("Target path is new. Pulling related structural interface points:")
            
            targets = fallbacks if fallbacks else ["agentic/codebase_guru/tools/graph_db.py"]
            for target in targets:
                t_clean = target.replace("\\", "/")[4:] if target.replace("\\", "/").startswith("src/") else target.replace("\\", "/")
                cypher = "MATCH (f:File {path: $path})-[:CONTAINS]->(m:Method) RETURN m.name AS name"
                with self.db.driver.session() as s:
                    res = s.run(cypher, path=t_clean)
                    methods = [r["name"] for r in res]
                    if methods:
                        context_lines.append(f" - Interface hooks from src/{t_clean}: {', '.join(methods)}")

        context_payload = "\n".join(context_lines) if context_lines else "No direct database dependencies mapped."

        return f"""{mode_header}
You are an execution brain operating within local hardware bounds (RTX 3060 / 8K context max).
Focus strictly on the target objective for the destination module specified below.

[DESTINATION MODULE TARGET]
src/{db_path}

[STRUCTURAL CONTEXT & DEPENDENCIES]
{context_payload}

[ACTIVE SOURCE STATE]
{code_block}

[OBJECTIVE]
> {objective}

[CRITICAL DIRECTIVES]
1. Output exact, concise modifications or creations suited for the target path.
2. Keep code implementations clean, production-ready, and wrapped in standard markdown blocks.
"""

    def close(self):
        self.db.close()
