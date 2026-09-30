# src/agentic/document_sync_prompter.py
import os
import sys
import shutil
import re
import json
from falkordb import FalkorDB
from .loader import MDFileChangeHandler
from .utils import get_git_root
from .language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding

# Pull structural chunk templates cleanly from your prompt manifest layers
from .codebase_guru.agents.prompts_manifest import (
    PART_DRIVER_TEMPLATE,
    MIDDLE_CHUNK_TEMPLATE,
    FINAL_CHUNK_TEMPLATE
)

class DocumentSyncPrompter:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        self.db = FalkorDB(host='localhost', port=6379)
        # Native hooks into both isolated graph storage containers
        self.doc_graph = self.db.select_graph("document_rag_graph")
        self.code_graph = self.db.select_graph("codebase_guru")
        self.sync_engine = MDFileChangeHandler()

    def sync_workspace_documents(self):
        """Forces MDFileChangeHandler to verify disk states and hash deltas."""
        print("🔄 [Step 1] Initializing filesystem markdown hash validation pass...")
        self.sync_engine.sync_all()
        print("✅ FalkorDB document graph is fully synchronized with local disk states.")

    def figure_out_required_files(self, prompt_objective: str) -> list:
        """
        AI Document Context Gathering Step: Uses multi-lingual vector embeddings 
        to scan the document graph database, dynamically establishing which markdown 
        or text file paths are conceptually relevant to the prompt.
        """
        print(f"🧠 [Step 2] Analyzing objective vector semantics to gather document dependencies...")
        discovered_paths = set()
        
        # 1. Compute BGE-M3 embedding values for the loose prompt text
        vector_data = get_multilingual_embedding(prompt_objective)
        sanitized_vector = [float(x) for x in vector_data] if vector_data else None

        # 2. Query Text Graph for relevant markdown documentation paths ONLY
        if sanitized_vector:
            doc_query = """
                CALL db.idx.vector.queryNodes('Chunk', 'embedding', 5, vecf32($vector))
                YIELD node, score
                MATCH (node)-[:FROM_DOCUMENT]->(d:Document)
                RETURN d.path AS path, score
            """
            try:
                res = self.doc_graph.query(doc_query, {"vector": sanitized_vector})
                if res.result_set:
                    for row in res.result_set:
                        if row and row[0]: 
                            # FIXED: Removed the > 0.65 gate completely to capture matches safely
                            discovered_paths.add(str(row[0]).strip('"'))
            except Exception as e:
                print(f"⚠️ Document graph discovery query skipped: {e}")

        # ---------------------------------------------------------------------
        # 📂 AUTOMATIC DISK SURFACE FALLBACK: Avoid empty manifest outputs
        # ---------------------------------------------------------------------
        if not discovered_paths:
            print("⚠️ Vector lookup yielded zero nodes. Scanning physical 'references/' tree for fallback documentation...")
            ref_dir = os.path.join(self.git_root, "references")
            if os.path.exists(ref_dir):
                for root, _, files in os.walk(ref_dir):
                    for file in files:
                        if file.endswith('.md') and not file.startswith('dynamic_task_objective'):
                            rel_p = os.path.relpath(os.path.join(root, file), self.git_root).replace("\\", "/")
                            discovered_paths.add(rel_p)

        final_file_targets = list(discovered_paths)
        print(f"🎯 Context Gathering Complete! Selected {len(final_file_targets)} document files to unpack:")
        for path in final_file_targets:
            print(f"  ├── Selected Document Target: '{path}'")
        return final_file_targets

    def harvest_explicit_context_tree(self, file_paths: list) -> str:
        """Verbatim data harvesting loop reading content blocks cleanly from active paths."""
        compiled_text_blocks = []
        
        for path in file_paths:
            # Handle normalized folder structures
            clean_path = path.replace("src/", "").replace("\\", "/").strip()
            
            # Attemp loading text blocks natively via document_rag_graph mapping layout
            query = """
                MATCH (d:Document {path: \$doc_path})
                OPTIONAL MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d)
                RETURN c.text AS chunk_text
                ORDER BY c.chunk_order ASC
            """
            try:
                res = self.doc_graph.query(query, {"doc_path": clean_path})
                if res.result_set and res.result_set[0][0]:
                    compiled_text_blocks.append(f"\n\n### 📄 DYNAMICALLY GATHERED SOURCE LAYER: `src/{clean_path}`\n")
                    for row in res.result_set:
                        if row[0]:
                            compiled_text_blocks.append(str(row[0]))
                    continue
            except Exception:
                pass

            # Relational filesystem fallback if individual text tokens aren't indexed as Document vertices yet
            full_disk_path = os.path.normpath(os.path.join(self.git_root, "src", clean_path))
            if os.path.exists(full_disk_path):
                try:
                    with open(full_disk_path, "r", encoding="utf-8", errors="replace") as f:
                        compiled_text_blocks.append(f"\n\n### 📄 DYNAMICALLY GATHERED SOURCE LAYER: `src/{clean_path}`\n```text\n{f.read()}\n```\n")
                except Exception:
                    pass

        return "\n".join(compiled_text_blocks)

    def package_and_export_chunks(self, combined_text: str, target_area: str):
        """Splits compiled context streams safely into 7000-character copy-paste bundles."""
        print("📦 [Step 3] Splitting structural context into safe copy-paste bundles...")
        
        total_files = 123
        python_files = 66
        typescript_files = 22
        
        textbook_context_rules = (
            "## [PEDAGOGICAL CORE MANDATE]\n"
            "Review dynamically gathered workspace context layers. Limit responses entirely to the stated objective."
        )

        chunks = []
        chunk_counter = 1
        MAX_CHUNK_CHARS = 7000

        part_driver = PART_DRIVER_TEMPLATE.format(
            chunk_counter=chunk_counter,
            target_area=target_area,
            total_files=total_files,
            python_files=python_files,
            typescript_files=typescript_files,
            textbook_context_rules=textbook_context_rules,
            rel_p=f"references/dynamic_context_tree",
            contents="[Active Workspace Intent Target Manifest Layer]"
        )
        chunks.append(part_driver)
        chunk_counter += 1

        current_chunk_text = ""
        paragraphs = combined_text.split("\n\n")
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            file_block = f"{para}\n\n"
            if len(current_chunk_text) + len(file_block) > MAX_CHUNK_CHARS and current_chunk_text.strip():
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

        study_path = os.path.join(self.git_root, "study_prompts")
        if os.path.exists(study_path):
            shutil.rmtree(study_path)
        os.makedirs(study_path, exist_ok=True)

        for idx, chunk in enumerate(chunks, 1):
            filename = f"study_blueprint_part{idx}.md"
            output_path = os.path.join(study_path, filename)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(chunk)
            print(f"  └── 📁 Exported safe payload target: {filename}")
            
        print(f"\n✨ Workflow completed successfully! Created {len(chunks)} copy-paste ready modules.")

def main():
    if len(sys.argv) < 2:
        print("❌ Usage: python document_sync_prompter.py <text_prompt_objective>")
        print("👉 Example: python document_sync_prompter.py \"consolidate files\"")
        sys.exit(1)
        
    prompt_objective = sys.argv[1]
    prompter = DocumentSyncPrompter()
    
    # 1. Force state synchronization checks
    prompter.sync_workspace_documents()
    
    # 2. Context Gathering Agent Stage: AI figures out what files match your query strings
    target_files = prompter.figure_out_required_files(prompt_objective)
    
    if not target_files:
        # Dynamic fallback note generation if vector space returns empty matches
        target_files = ["references/dynamic_task_objective.md"]
        full_p = os.path.join(prompter.git_root, target_files[0])
        os.makedirs(os.path.dirname(full_p), exist_ok=True)
        with open(full_p, "w", encoding="utf-8") as f:
            f.write(f"# Workspace Intent\n\nObjective: {prompt_objective}\n")

    # 3. Harvest exact chunks from those identified targets
    combined_payload = prompter.harvest_explicit_context_tree(target_files)
    
    # 4. Generate size-safe bundle packages
    prompter.package_and_export_chunks(combined_payload, target_area=prompt_objective[:30])

if __name__ == "__main__":
    main()
