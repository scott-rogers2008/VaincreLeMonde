import subprocess
import os
from tools.parser import CodebaseParser
from tools.embedder import LocalEmbedder
from tools.graph_db import CodebaseGraphManager

class GitSyncManager:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.parser = CodebaseParser(root_dir=root_dir)
        self.embedder = LocalEmbedder()
        self.db = CodebaseGraphManager()

    def get_modified_and_untracked_files(self) -> list:
        """Queries local Git binaries to find modified or uncommitted files."""
        files_to_sync = set()
        try:
            # 1. Get modified files that are tracked by Git
            tracked_output = subprocess.check_output(
                ["git", "diff", "--name-only"], 
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            
            # 2. Get untracked files (new files not yet committed)
            untracked_output = subprocess.check_output(
                ["git", "status", "--porcelain"], 
                cwd=self.root_dir, stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()

            # Parse tracked files
            if tracked_output:
                for f in tracked_output.split("\n"):
                    if f.endswith(".py"):
                        files_to_sync.add(f)

            # Parse untracked files (lines starting with '??')
            if untracked_output:
                for line in untracked_output.split("\n"):
                    if line.startswith("??"):
                        f = line[3:].strip()
                        if f.endswith(".py"):
                            files_to_sync.add(f)
                            
        except Exception as e:
            print(f"⚠️ Git command failed. Is Git initialized in this folder? Error: {e}")
            
        return list(files_to_sync)

    def sync_deltas(self):
        """Processes and vectorizes only the modified code files."""
        changed_files = self.get_modified_and_untracked_files()
        
        if not changed_files:
            print("✨ Everything is up to date. No Git deltas found.")
            return

        print(f"📦 Found {len(changed_files)} changed files. Beginning delta sync...")
        self.db.initialize_indexes()

        for rel_path in changed_files:
            full_path = os.path.join(self.root_dir, rel_path)
            if not os.path.exists(full_path):
                print(f"🗑️ File deleted locally, skipping: {rel_path}")
                continue

            print(f"🔄 Syncing file: {rel_path}")
            file_info = self.parser.parse_file(full_path)
            
            # Sync the core file node structure
            self.db.sync_file_node(rel_path, file_info["file_hash"])
            
            # Sync changed methods and automatically trigger history tracking
            for func in file_info["functions"]:
                body_vector = self.embedder.get_embedding(func["body"])
                doc_vector = self.embedder.get_embedding(func["docstring"]) if func["docstring"] else []
                
                self.db.sync_method_and_docs(
                    file_path=rel_path,
                    method_data=func,
                    body_vector=body_vector,
                    doc_vector=doc_vector
                )
        
        self.db.close()
        print("✅ Delta sync complete!")

if __name__ == "__main__":
    # Test run on your current folder path
    current_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    syncer = GitSyncManager(root_dir=current_repo)
    syncer.sync_deltas()
