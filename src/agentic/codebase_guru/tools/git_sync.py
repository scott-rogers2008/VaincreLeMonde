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
        files_to_sync = set()
        target_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        try:
            tracked = subprocess.check_output(
                ["git", "diff", "HEAD", "--name-only"], cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if tracked:
                for f in tracked.split("\n"):
                    if f.lower().endswith(target_extensions):
                        files_to_sync.add(f)

            untracked = subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if untracked:
                for line in untracked.split("\n"):
                    if line.startswith("??"):
                        f = line[3:].strip()
                        if f.lower().endswith(target_extensions):
                            files_to_sync.add(f)

            recent_commits = subprocess.check_output(
                ["git", "log", "-n", "5", "--name-only", "--pretty=format:"],
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if recent_commits:
                for f in recent_commits.split("\n"):
                    clean_f = f.strip()
                    if clean_f.lower().endswith(target_extensions):
                        files_to_sync.add(clean_f)
        except Exception as e:
            print(f"⚠️ Git comprehensive delta capture failed: {e}")
        return list(files_to_sync)

    def sync_deltas(self):
        changed_files = self.get_modified_and_untracked_files()
        if not changed_files:
            print("✨ Everything is up to date. No Git deltas found.")
            return

        print(f"📦 Found {len(changed_files)} candidate change scopes. Verifying fingerprints...")
        self.db.initialize_indexes()

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
            
            # CRITICAL FIX: Strip 'src/' prefix immediately if present to align with DB keys!
            db_rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
            if db_rel_path.startswith("src/"):
                db_rel_path = db_rel_path[4:]

            if not os.path.exists(full_path):
                # ONLY prompt for removal if the database was actually tracking it!
                if db_rel_path in existing_hashes:
                    print(f"\n🗑️ Detected Deleted File Reference: 'src/{db_rel_path}'")
                    confirm = input("❓ Remove this file reference from FalkorDB? (y/n): ").strip().lower()
                    if confirm == 'y':
                        purged = self.db.purge_file_cascade(db_rel_path)
                        if purged:
                            print(f"✅ Expunged '{db_rel_path}' from FalkorDB.")
                else:
                    # It's a historical artifact from git log that isn't in our clean DB; skip silently
                    pass
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
