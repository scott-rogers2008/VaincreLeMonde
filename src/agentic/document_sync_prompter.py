# src/agentic/document_sync_prompter.py
import os
import sys
import shutil
from falkordb import FalkorDB
from .loader import MDFileChangeHandler
from .utils import get_git_root
from .language_tutor.tools.embeddings import get_embeddings as get_multilingual_embedding
from .document_concept_agent import DocumentConceptAgent

from .codebase_guru.agents.prompts_manifest import (
    DOC_DRIVER_TEMPLATE,
    MIDDLE_CHUNK_TEMPLATE,
    FINAL_CHUNK_TEMPLATE
)

class DocumentSyncPrompter:
    def __init__(self):
        self.git_root = os.path.abspath(get_git_root(os.curdir))
        self.db = FalkorDB(host='localhost', port=6379)
        self.doc_graph = self.db.select_graph("document_rag_graph")
        self.sync_engine = MDFileChangeHandler()
        self.concept_agent = DocumentConceptAgent()

    def sync_workspace_documents(self):
        """Forces MDFileChangeHandler to verify disk states and hash deltas."""
        print("🔄 [Step 1] Initializing filesystem markdown hash validation pass...")
        self.sync_engine.sync_all()
        print("✅ FalkorDB document graph is fully synchronized with local disk states.")

    def figure_out_required_files(self, prompt_objective: str) -> list:
        """AI Context Gathering: Dynamically scans document text nodes via vector proximity."""
        print(f"🧠 [Step 2] Analyzing objective vector semantics to gather document dependencies...")
        discovered_paths = set()

        routing_decision = self.concept_agent.determine_retrieval_strategy(prompt_objective)
        strategy = routing_decision.get("strategy", "NARROW_VECTOR")
        reasoning = routing_decision.get("reasoning", "")      
        print(f"🤖 [Agent Routing Matrix] Selected Strategy: {strategy}")
        print(f"   └── Reason: {reasoning}")

        if strategy == "GLOBAL_SWEEP":
            print("🚀 Global repository mode activated. Initializing complete directory extraction...")
        else:
            vector_data = get_multilingual_embedding(prompt_objective)
            if not vector_data or not isinstance(vector_data, list):
                print("⚠️ Failed to generate embedding vector for prompt routing.")
                return []
            sanitized_vector = [float(x) for x in vector_data]

            doc_query = """
                CALL db.idx.vector.queryNodes('Chunk', 'embedding', 100, vecf32($vector))
                YIELD node, score
                MATCH (node)-[:FROM_DOCUMENT]->(d:Document)
                RETURN d.path AS path, score
            """
            try:
                res = self.doc_graph.query(doc_query, {"vector": sanitized_vector})
                if res.result_set:
                    for row in res.result_set:
                        if row and row[0]: 
                            discovered_paths.add(str(row[0]).strip('"'))
            except Exception as e:
                print(f"⚠️ Document graph discovery query skipped: {e}")

        # Direct physical filesystem backup scan pass to guarantee context payload safety
        if not discovered_paths or strategy == "GLOBAL_SWEEP":
            print("🔍 Harvesting references, books, goals, and training folders directly from disk...")
            target_dirs = ["references", "books", "goals", "training"]
            for folder_name in target_dirs:
                target_path = os.path.join(self.git_root, folder_name)
                if not os.path.exists(target_path):
                    target_path = os.path.join(self.git_root, "src", folder_name)
                    
                if os.path.exists(target_path):
                    for root, _, files in os.walk(target_path):
                        for file in files:
                            if file.endswith('.md'):
                                rel_p = os.path.relpath(os.path.join(root, file), self.git_root).replace("\\", "/")
                                discovered_paths.add(rel_p)

        final_file_targets = list(discovered_paths)
        print(f"🎯 Context Gathering Complete! Selected {len(final_file_targets)} document files to unpack:")
        for path in final_file_targets:
            print(f"  ├── Selected Document Target: '{path}'")
        return final_file_targets

    def harvest_explicit_context_tree(self, file_paths: list) -> list:
        """Verbatim data harvesting loop reading content blocks cleanly from active paths.
        Guarantees that each unique document path results in exactly ONE consolidated block element.
        """
        compiled_text_blocks = []
        
        for path in file_paths:
            clean_path = path.replace("src/", "").replace("\\", "/").strip()
            file_header = f"\n\n### 📄 DYNAMICALLY GATHERED SOURCE LAYER: `src/{clean_path}`\n"
            file_body = ""

            if "dynamic_context_tree" in clean_path:
                continue
            
            query = """
                MATCH (d:Document {path: \$doc_path})
                OPTIONAL MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d)
                RETURN c.text AS chunk_text
                ORDER BY c.chunk_order ASC
            """
            try:
                res = self.doc_graph.query(query, {"doc_path": clean_path})
                if res.result_set and len(res.result_set) > 0:
                    chunks_accumulator = []
                    for row in res.result_set:
                        if row and row[0]:
                            chunks_accumulator.append(str(row[0]))
                    if chunks_accumulator:
                        file_body = "\n".join(chunks_accumulator)
                        # Fix: Append as a single complete text block item to preserve file counting logic
                        compiled_text_blocks.append(f"{file_header}{file_body}\n")
                        continue
            except Exception:
                pass

            # Filesystem fallback verification pass
            full_disk_path = os.path.normpath(os.path.join(self.git_root, clean_path))
            if not os.path.exists(full_disk_path):
                full_disk_path = os.path.normpath(os.path.join(self.git_root, "src", clean_path))
                
            if os.path.exists(full_disk_path):
                try:
                    with open(full_disk_path, "r", encoding="utf-8", errors="replace") as f:
                        file_body = f.read()
                        compiled_text_blocks.append(f"{file_header}```text\n{file_body}\n```\n")
                except Exception:
                    pass

        return compiled_text_blocks

    def package_and_export_chunks(self, compiled_text_blocks: list, target_area: str):
        """Intelligently bundles gathered documents into clean files without cutting code/paragraphs."""
        print("📦 [Step 3] Splitting structural context into safe copy-paste bundles...")

        total_files = self.sync_engine.get_number_of_indexed_documents()
        # Correctly tracks unique files provided instead of database graph text chunks
        provided_files = len(compiled_text_blocks)
        
        textbook_context_rules = (
            "## [PEDAGOGICAL CORE MANDATE]\n"
            "Review dynamically gathered workspace context layers. Limit responses entirely to the stated objective."
        )

        chunks = []
        chunk_counter = 1
        MAX_CHUNK_CHARS = 7000

        # Build initial template package preview cleanly
        preview_text = "\n".join(compiled_text_blocks)[:3000] if compiled_text_blocks else ""
        part_driver = DOC_DRIVER_TEMPLATE.format(
            chunk_counter=chunk_counter,
            target_area=target_area,
            total_files=total_files,
            provided_files=provided_files,
            textbook_context_rules=textbook_context_rules
        )
        chunks.append(part_driver)
        chunk_counter += 1

        current_chunk_text = ""
        
        for document_block in compiled_text_blocks:
            # Safe verification: Check if a singular text node asset exceeds the threshold natively
            if len(document_block) > MAX_CHUNK_CHARS:
                # Optimized fallback split loop: Slice cleanly by lines instead of double newlines
                # to prevent massive code strings from spilling past limits or truncating raw fences
                sub_lines = document_block.split("\n")
                for line in sub_lines:
                    formatted_line = f"{line}\n"
                    if len(current_chunk_text) + len(formatted_line) > MAX_CHUNK_CHARS:
                        if current_chunk_text.strip():
                            chunks.append(MIDDLE_CHUNK_TEMPLATE.format(chunk_counter=chunk_counter, current_chunk_text=current_chunk_text))
                            chunk_counter += 1
                        current_chunk_text = formatted_line
                    else:
                        current_chunk_text += formatted_line
            else:
                if len(current_chunk_text) + len(document_block) > MAX_CHUNK_CHARS:
                    if current_chunk_text.strip():
                        chunks.append(MIDDLE_CHUNK_TEMPLATE.format(chunk_counter=chunk_counter, current_chunk_text=current_chunk_text))
                        chunk_counter += 1
                    current_chunk_text = document_block
                else:
                    current_chunk_text += document_block

        if current_chunk_text.strip():
            chunks.append(FINAL_CHUNK_TEMPLATE.format(chunk_counter=chunk_counter, current_chunk_text=current_chunk_text))

        # Output the structural data blueprints safely to disk
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
    
    prompter.sync_workspace_documents()
    target_files = prompter.figure_out_required_files(prompt_objective)
    combined_payload = prompter.harvest_explicit_context_tree(target_files)
    prompter.package_and_export_chunks(combined_payload, target_area=prompt_objective[:30])

if __name__ == "__main__":
    main()