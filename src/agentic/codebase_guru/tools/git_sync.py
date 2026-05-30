import os
from .parser import CodebaseParser
from .embedder import LocalEmbedder
from .graph_db import CodebaseGraphManager
from ..utils import get_git_root

class GitSyncManager:
    def __init__(self):
        # 1. Use your existing utility to find the repository root folder
        git_root = get_git_root(os.curdir)
        self.root_dir = os.path.abspath(git_root)
            
        print(f"🏠 Real Repository Root detected via utils: {self.root_dir}")
        self.parser = CodebaseParser(root_dir=self.root_dir)
        self.embedder = LocalEmbedder()
        self.db = CodebaseGraphManager()

    def get_modified_and_untracked_files(self) -> list:
        """Queries local Git binaries to find modified or uncommitted files."""
        import subprocess
        files_to_sync = set()
        try:
            # Run commands directly from the real repository root
            tracked_output = subprocess.check_output(
                ["git", "diff", "--name-only"], 
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            
            untracked_output = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()

            if tracked_output:
                for f in tracked_output.split("\n"):
                    if f.endswith(".py"):
                        files_to_sync.add(f)

            if untracked_output:
                for line in untracked_output.split("\n"):
                    if line.startswith("??"):
                        f = line[3:].strip()
                        if f.endswith(".py"):
                            files_to_sync.add(f)
                            
        except Exception as e:
            print(f"⚠️ Git command failed: {e}")
            
        return list(files_to_sync)

    def sync_deltas(self):
        """Processes and vectorizes only the modified code files securely."""
        changed_files = self.get_modified_and_untracked_files()
        
        if not changed_files:
            print("✨ Everything is up to date. No Git deltas found.")
            return

        print(f"📦 Found {len(changed_files)} changed files. Beginning delta sync...")
        self.db.initialize_indexes()

        for rel_path in changed_files:
            # Resolve the absolute disk path correctly using the Git root anchor
            full_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
            
            # Match the relative format your main ingestion script saves to Neo4j
            # Your main.py saves paths relative to git_root/src, so we replicate that calculation
            src_dir = os.path.join(self.root_dir, "src")
            db_rel_path = os.path.relpath(full_path, src_dir).replace("\\", "/")

            if not os.path.exists(full_path):
                print(f"🗑️ File deleted locally, skipping: {db_rel_path}")
                continue

            print(f"🔄 Syncing file changes into graph: {db_rel_path}")
            file_info = self.parser.parse_file(full_path)
            
            # Check for corrupted parses
            if "error" in file_info or "file_hash" not in file_info:
                continue

            self.db.sync_file_node(db_rel_path, file_info["file_hash"])
            
            for func in file_info["functions"]:
                body_vector = self.embedder.get_embedding(func["body"])
                doc_vector = self.embedder.get_embedding(func["docstring"]) if func["docstring"] else []
                
                self.db.sync_method_and_docs(
                    file_path=db_rel_path,
                    method_data=func,
                    body_vector=body_vector,
                    doc_vector=doc_vector
                )
        
        self.db.close()
        print("✅ Delta sync complete!")

if __name__ == "__main__":
    syncer = GitSyncManager()
    syncer.sync_deltas()