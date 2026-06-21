# src/agentic/codebase_guru/tools/git_sync.py
import os
import subprocess
from .parser import CodebaseParser
from .embedder import LocalEmbedder
from .graph_db import CodebaseGraphManager

class GitSyncManager:
    def __init__(self):
        from .utils import get_git_root
        self.root_dir = os.path.abspath(get_git_root(os.curdir))
        print(f" Real Repository Root detected: {self.root_dir}")
        self.parser = CodebaseParser(root_dir=self.root_dir)
        self.embedder = LocalEmbedder()
        self.db = CodebaseGraphManager()

    def get_modified_and_untracked_files(self) -> list:
        """Queries Git status porcelain to catch all un-staged modifications and raw untracked files."""
        files_to_sync = set()
        target_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        try:
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if status_output:
                for line in status_output.split("\n"):
                    if len(line) < 4: continue
                    file_path = line[3:].strip()
                    if file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]
                    if file_path.lower().endswith(target_extensions):
                        files_to_sync.add(file_path)
        except Exception as e:
            print(f"⚠️ Git porcelain status trace failed: {e}")
        return list(files_to_sync)

    # --- CRITICAL PROTECTION PASS: INTERCEPT MISSING GRAPH FILE NODES NATIVELY ---
    def identify_missing_database_nodes(self, existing_hashes: dict) -> list:
        """
        Scans the local filesystem disk tree to locate structural target files 
        that aren't indexed inside the active FalkorDB instance.
        """
        missing_from_db = []
        target_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        exclude_dirs = {'.git', '.venv', '.wvenv', 'node_modules', 'dist', 'build'}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            for file in files:
                if file.lower().endswith(target_extensions):
                    full_path = os.path.join(root, file)
                    db_rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                    if db_rel_path.startswith("src/"):
                        db_rel_path = db_rel_path[4:]
                    
                    # If file is on disk but completely absent from the graph nodes index register
                    if db_rel_path not in existing_hashes:
                        missing_from_db.append(os.path.relpath(full_path, self.root_dir))
        return missing_from_db

    def sync_deltas(self):
        """Processes and vectorizes modified, untracked, or missing files using FalkorDB fingerprints."""
        self.db.initialize_indexes()
        
        # 1. Gather all pre-existing signatures natively via FalkorDB openCypher
        existing_hashes = {}
        try:
            res = self.db.graph.query("MATCH (f:File) RETURN f.path AS path, f.hash AS hash")
            for record in res.result_set:
                f_path = str(record[0]).strip('"')
                f_hash = str(record[1]).strip('"')
                if f_path:
                    existing_hashes[f_path] = f_hash
        except Exception as e:
            print(f"⚠️ Pre-indexing fingerprint trace skipped: {e}")

        # 2. Combine files changed in Git with files completely missing from the database
        porcelain_changes = self.get_modified_and_untracked_files()
        missing_db_changes = self.identify_missing_database_nodes(existing_hashes)
        
        # Merge tracking targets to remove duplicates
        changed_files = list(set(porcelain_changes + missing_db_changes))

        if not changed_files:
            print("✨ Everything is up to date. No Git changes or missing graph entries found.")
            return

        print(f"📦 Found {len(changed_files)} files requiring index processing. Syncing metrics configurations...")

        for rel_path in changed_files:
            full_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
            db_rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
            if db_rel_path.startswith("src/"):
                db_rel_path = db_rel_path[4:]

            if not os.path.exists(full_path):
                if db_rel_path in existing_hashes:
                    print(f"\n🗑️ Detected Deleted File Reference: 'src/{db_rel_path}'")
                    confirm = input("❓ Remove this file reference from FalkorDB? (y/n): ").strip().lower()
                    if confirm == 'y':
                        purged = self.db.purge_file_cascade(db_rel_path)
                        if purged: print(f"✅ Expunged '{db_rel_path}' from FalkorDB.")
                continue

            file_info = self.parser.parse_file(full_path)
            if "error" in file_info or "file_hash" not in file_info:
                continue

            live_hash = file_info["file_hash"]
            # Skip only if the file exists in the database and its hash matches exactly
            if db_rel_path in existing_hashes and existing_hashes[db_rel_path] == live_hash:
                continue

            print(f"🔄 Syncing module indices into FalkorDB codebase graph: src/{db_rel_path}")
            self.db.sync_file_node(db_rel_path, live_hash)

            all_structural_blocks = file_info.get("functions", []) + file_info.get("classes", [])
            for func in all_structural_blocks:
                func_name = func.get("name", "anonymous")
                func_body = func.get("body", "")
                if not func_body: continue
                vector_chunks = self.embedder.get_embeddings_for_piece(func_body)
                self.db.sync_chunked_method_data(
                    file_path=db_rel_path,
                    method_name=func_name,
                    method_data=func,
                    vector_chunks=vector_chunks
                )
        print("✅ FalkorDB Delta sync operation completed.")

if __name__ == "__main__":
    syncer = GitSyncManager()
    syncer.sync_deltas()
