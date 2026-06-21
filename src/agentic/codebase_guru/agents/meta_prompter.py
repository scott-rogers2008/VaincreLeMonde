# src/agentic/codebase_guru/agents/meta_prompter.py
import os
import requests
from .utils import get_git_root
from falkordb import FalkorDB
from .prompts_manifest import (
    PART_DRIVER_TEMPLATE,
    MIDDLE_CHUNK_TEMPLATE,
    FINAL_CHUNK_TEMPLATE,
    ESCALATION_PROMPT_TEMPLATE
)

class AdvancedMetaPrompter:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        # Pure exclusion set matching standard system properties
        self.exclude_dirs = {
            '.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', 
            '.vs', '.angular', '.vscode', 'node_modules', "angular", 
            'dist', 'browser', 'out', 'build', '__pycache__'
        }

    def _query_ingested_textbook_rules(self, target_area: str, improvement_goal: str, limit: int = 3) -> str:
        """
        Queries pre-existing nodes built by loader.py. Handles multi-lingual semantic vectors
        and extracts rules directly from the book markdown content to guide prompt building.
        """
        search_phrase = f"{target_area} {improvement_goal}"
        try:
            # Generate a 1024D vector to perfectly align with loader.py's bge-m3 mapping specs
            res = requests.post("http://localhost:11434/api/embeddings", json={"model": "bge-m3", "prompt": search_phrase}, timeout=10)
            vector = res.json()["embeddings"] if res.status_code == 200 else None
        except Exception:
            vector = None

        if not vector:
            return "## [PEDAGOGICAL CORE MANDATE]\nLimit outputs strictly to meta-prompts. Prohibit direct functional updates."

        # openCypher Query: Locate chunks whose parent document path originates within the books tree
        query = """
        CALL db.idx.vector.queryNodes('Chunk', 'embedding', $limit, vecf32($vector)) YIELD node, score
        MATCH (node)-[:FROM_DOCUMENT]->(d:Document)
        WHERE d.path CONTAINS 'books/Understanding_This/'
        RETURN d.path AS chapter, node.text AS rule_text, score
        """
        
        extracted_rules = []
        try:
            results = self.doc_graph.query(query, {"limit": limit, "vector": vector})
            for row in results.result_set:
                chapter_path = row[0]
                rule_text = row[1]
                match_score = float(row[2])
                extracted_rules.append(f"📘 [INGESTED CURRICULUM RULE: {chapter_path} (Proximity Score: {match_score:.4f})]\n{rule_text}")
        except Exception as e:
            return f"// Error extracting multi-lingual book content from graph space: {e}"

        return "\n\n".join(extracted_rules) if extracted_rules else "No matching curriculum guardrails extracted from database text layers."


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
            part_driver = PART_DRIVER_TEMPLATE.format(
                chunk_counter=chunk_counter,
                target_area=target_area,
                total_files=stats['total_files'],
                python_files=stats['python_files'],
                typescript_files=stats['typescript_files'],
                textbook_context_rules=textbook_context_rules,
                rel_p=rel_p,
                contents=contents
            )
            chunks.append(part_driver)
            chunk_counter += 1

        MAX_CHUNK_CHARS = 7000
        current_chunk_text = ""
        
        for rel_p, contents in packaged_files:
            file_block = f"### 📄 TARGET AREA SOURCE: `{rel_p}`\n```text\n{contents}\n```\n\n"
            if len(current_chunk_text) + len(file_block) > MAX_CHUNK_CHARS and current_chunk_text.strip():
                # CRITICAL SAFETY UNIFICATION: Injected constraints into target file payload headers
                chunk_payload = MIDDLE_CHUNK_TEMPLATE.format(
                    chunk_counter=chunk_counter,
                    current_chunk_text=current_chunk_text
                )
                chunks.append(chunk_payload)
                chunk_counter += 1
                current_chunk_text = file_block
            else:
                current_chunk_text += file_block

        if current_chunk_text.strip():
            chunk_payload = FINAL_CHUNK_TEMPLATE.format(
                chunk_counter=chunk_counter,
                current_chunk_text=current_chunk_text
            )
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
        textbook_context_rules = self._query_ingested_textbook_rules(failed_task, "")
        return ESCALATION_PROMPT_TEMPLATE.format(
            total_files=repo_stats["total_files"],
            python_files=repo_stats["python_files"],
            typescript_files=repo_stats["typescript_files"],
            textbook_context_rules=textbook_context_rules,
            failed_task=failed_task,
            loop_history=loop_history,
            graph_context=graph_context
        )
