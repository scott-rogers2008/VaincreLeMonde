import os
import json
from ..utils import get_git_root

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
            # Try sliding into src/ if the base anchor is offset
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

    def generate_refactoring_prompt(self, target_file_path: str, improvement_goal: str) -> str:
        """
        Gathers the target code file, scans for core connected pipeline tools,
        and builds a high-density, context-complete blueprint engineering prompt.
        """
        stats = self._analyze_tutor_infrastructure()
        
        # 1. Read the exact live file you want to change
        primary_code = self._safe_read_file(target_file_path)
        
        # 2. DYNAMIC LOOKUP: Automatically pack critical infrastructure tools 
        # so the model can verify cross-file signatures and import boundaries
        parser_code = self._safe_read_file("agentic/codebase_guru/tools/parser.py")
        db_code = self._safe_read_file("agentic/codebase_guru/tools/graph_db.py")
        sync_code = self._safe_read_file("agentic/codebase_guru/tools/git_sync.py")
        
        prompt = f"""### SYSTEM INSTRUCTION
You are a Principal Software Architect specializing in advanced agentic infrastructure and human learning systems.
We are modifying a complex multi-language codebase (Python and TypeScript) using a local Neo4j vector graph layer. 

Your objective is to provide a production-ready, typed implementation resolving the modification goal. You are provided with the absolute full contents of the primary files involved to eliminate guesswork regarding import pipelines or existing schema definitions.

---

### 📊 ENVIRONMENT STATS
* **Repository Root**: `{self.git_root}`
* **Total Mapped Footprint**: {stats['total_files']} files ({stats['python_files']} Python, {stats['typescript_files']} TypeScript)

---

### 🎯 REFURBISHMENT TARGET
* **Primary Target File**: `{target_file_path}`
* **Improvement Goal**: 
> {improvement_goal}

---

### 📝 FULL LIVE FILE SOURCE (THE TARGET TO REWRITE)
Below is the complete active code for `{target_file_path}`:
```python
{primary_code}
```

---

### 🔌 DECOUPLED PIPELINE CONTEXT (FOR IMPORT & DATA ALIGNMENT)
To guarantee your refactored code aligns perfectly with our path rules, hash utilities, and database schemas, use the live implementations of our background tool modules below as your absolute reference:

#### 1. File Tracker (`agentic/codebase_guru/tools/parser.py`)
```python
{parser_code}
```

#### 2. Neo4j Graph Driver (`agentic/codebase_guru/tools/graph_db.py`)
```python
{db_code}
```

#### 3. Differential Sync Manager (`agentic/codebase_guru/tools/git_sync.py`)
```python
{sync_code}
```

---

### 📥 EXPECTED ARCHITECTURAL RESPONSE FORMAT
Please process this full-context blueprint payload and return your engineering deliverables:
1. **Structural Analysis**: Identify any implicit defects, type gaps, or path traps between the primary file and the background modules.
2. **Complete Refactored Implementation**: Provide the 100% complete, rewritten source file block for the Primary Target File. Do not truncate code or write placeholders like `# ... rest of code`. Every method must be fully written out.
3. **Graph Update Path**: Provide the exact Cypher or schema directions needed to keep node parameters consistent with your updates.
"""
        return prompt

    def export_prompt_to_file(self, prompt_content: str, filename="refactor_blueprint.md"):
        output_path = os.path.join(self.git_root, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt_content)
        print(f"📁 Context-complete engineering prompt exported to: {output_path}")
