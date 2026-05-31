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
        """Queries local Git binaries to find modified or uncommitted files across all target languages."""
        import subprocess
        files_to_sync = set()
        
        # Define our global multi-language matching extensions
        target_extensions = ('.py', '.ts', '.tsx', '.js', '.jsx')
        
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
                    if f.lower().endswith(target_extensions):
                        files_to_sync.add(f)

            if untracked_output:
                for line in untracked_output.split("\n"):
                    if line.startswith("??"):
                        f = line[3:].strip()
                        if f.lower().endswith(target_extensions):
                            files_to_sync.add(f)
                            
        except Exception as e:
            print(f"⚠️ Git command failed: {e}")
            
        return list(files_to_sync)

    def sync_deltas(self):
        """Processes and vectorizes only the modified code files securely skipping unchanged hashes."""
        changed_files = self.get_modified_and_untracked_files()
        
        if not changed_files:
            print("✨ Everything is up to date. No Git deltas found.")
            return

        print(f"📦 Found {len(changed_files)} changed files. Checking database matches...")
        self.db.initialize_indexes()

        # --- PRE-EXISTING HASH MEMORY FILTER ---
        # Pull what Neo4j already holds to eliminate unnecessary re-indexing loops
        existing_hashes = {}
        with self.db.driver.session() as session:
            result = session.run("MATCH (f:File) RETURN f.path AS path, f.hash AS hash")
            for record in result:
                if record["path"]:
                    existing_hashes[record["path"]] = record["hash"]

        for rel_path in changed_files:
            # Resolve the absolute disk path correctly using the Git root anchor
            full_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
            
            # --- CRITICAL FIX: UNIFY WITH PARSER PATH LAYOUT ---
            # Your custom CodebaseParser evaluates paths relative to self.root_dir (Git Root)
            # We must use the exact same base string so database keys match 1:1!
            db_rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")

            # --- DYNAMIC FILE DELETION CLEANUP ---
            if not os.path.exists(full_path):
                print(f"\n🗑️  Detected Deleted File Reference: '{db_rel_path}'")
                confirm = input(f"❓ Do you want to remove this file and its methods from Neo4j? (y/n): ").strip().lower()
                
                if confirm == 'y':
                    purged = self.db.purge_file_cascade(db_rel_path)
                    if purged:
                        print(f"✅ Successfully expunged '{db_rel_path}' from the database context.")
                    else:
                        print(f"⚠️ Note: No node matched '{db_rel_path}' inside Neo4j. Skipping.")
                continue

            # --- PARSE FILE AND CHECK FINGERPRINT ALIGNMENT ---
            file_info = self.parser.parse_file(full_path)
            if "error" in file_info or "file_hash" not in file_info:
                continue

            live_hash = file_info["file_hash"]
            
            # Now, db_rel_path matches character-for-character with file_info["file_path"]
            if db_rel_path in existing_hashes and existing_hashes[db_rel_path] == live_hash:
                print(f"⏭️  Winters-edge bypass: Unchanged script skipped: {db_rel_path}")
                continue

            print(f"🔄 Syncing file changes into graph: {db_rel_path}")
            self.db.sync_file_node(db_rel_path, live_hash)
            
            # Combine both functions and classes to capture frontend structures
            all_structural_blocks = file_info.get("functions", []) + file_info.get("classes", [])
            
            for func in all_structural_blocks:
                func_name = func.get("name", "anonymous")
                func_body = func.get("body", "")
                if not func_body:
                    continue
                    
                # Process chunks through sliding window
                vector_chunks = self.embedder.get_embeddings_for_piece(func_body)
                
                self.db.sync_chunked_method_data(
                    file_path=db_rel_path,
                    method_name=func_name,
                    method_data=func,
                    vector_chunks=vector_chunks
                )

        self.db.close()
        print("✅ Delta sync complete!")

if __name__ == "__main__":
    syncer = GitSyncManager()
    syncer.sync_deltas()
