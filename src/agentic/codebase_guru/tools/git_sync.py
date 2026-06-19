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
        print(f"🏠 Real Repository Root detected: {self.root_dir}")
        self.parser = CodebaseParser(root_dir=self.root_dir)
        self.embedder = LocalEmbedder()
        self.db = CodebaseGraphManager()

    def get_modified_and_untracked_files(self) -> list:
        """
        Queries Git status porcelain to catch all un-staged modifications 
        and raw untracked files instantly without requiring 'git add'.
        """
        files_to_sync = set()
        target_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        
        try:
            # --porcelain is perfect here: 
            # '??' means untracked new file
            # ' M' or 'M ' means modified file (staged or unstaged)
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            
            if status_output:
                for line in status_output.split("\n"):
                    if len(line) < 4:
                        continue
                    
                    # Isolate the file path from the Git status prefix code
                    git_prefix = line[:2]
                    file_path = line[3:].strip()
                    
                    # Strip any surrounding quotes Git might add for special characters
                    if file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]

                    # Process the target if it matches our active programming domains
                    if file_path.lower().endswith(target_extensions):
                        files_to_sync.add(file_path)

        except Exception as e:
            print(f"⚠️ Git comprehensive porcelain status trace failed: {e}")
            
        return list(files_to_sync)

    def sync_deltas(self):
        """Processes and vectorizes modified or untracked files using FalkorDB fingerprints."""
        changed_files = self.get_modified_and_untracked_files()
        if not changed_files:
            print("✨ Everything is up to date. No Git changes found.")
            return

        print(f"📦 Found {len(changed_files)} active change scopes. Verifying fingerprints...")
        self.db.initialize_indexes()

        # Gather pre-existing signatures natively via FalkorDB openCypher
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

        for rel_path in changed_files:
            full_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
            
            # Normalize path tracking properties to align with structural keys
            db_rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
            if db_rel_path.startswith("src/"):
                db_rel_path = db_rel_path[4:]

            if not os.path.exists(full_path):
                # Only prompt for removal if the graph database was actively tracking it
                if db_rel_path in existing_hashes:
                    print(f"\n🗑️ Detected Deleted File Reference: 'src/{db_rel_path}'")
                    confirm = input("❓ Remove this file reference from FalkorDB? (y/n): ").strip().lower()
                    if confirm == 'y':
                        purged = self.db.purge_file_cascade(db_rel_path)
                        if purged:
                            print(f"✅ Expunged '{db_rel_path}' from FalkorDB.")
                continue

            file_info = self.parser.parse_file(full_path)
            if "error" in file_info or "file_hash" not in file_info:
                continue

            live_hash = file_info["file_hash"]
            if db_rel_path in existing_hashes and existing_hashes[db_rel_path] == live_hash:
                continue

            print(f"🔄 Syncing file changes into FalkorDB graph: {db_rel_path}")
            self.db.sync_file_node(db_rel_path, live_hash)

            all_structural_blocks = file_info.get("functions", []) + file_info.get("classes", [])
            for func in all_structural_blocks:
                func_name = func.get("name", "anonymous")
                func_body = func.get("body", "")
                if not func_body:
                    continue
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
