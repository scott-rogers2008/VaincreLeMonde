import os
from tools.parser import CodebaseParser
from tools.embedder import LocalEmbedder
from tools.graph_db import CodebaseGraphManager
from utils import get_git_root

def run_ingestion(target_repo_path):
    print(f"🚀 Starting Codebase Guru ingestion for: {target_repo_path}")
    
    # 1. Initialize your custom tools
    parser = CodebaseParser(root_dir=target_repo_path)
    embedder = LocalEmbedder()
    db = CodebaseGraphManager()
    
    # Ensure indexes and constraints are active
    db.initialize_indexes()
    
    # 2. Parse the codebase files using your custom parser rules
    print("🔍 Scanning directories and executing Node/Python extraction sub-agents...")
    parsed_files = parser.scan_codebase()
    
    # 3. Synchronize cleanly with Neo4j
    for file_info in parsed_files:
        if not file_info or "error" in file_info or "file_hash" not in file_info:
            print(f"⏩ Skipping database sync for broken file reference: {file_info.get('file_path', 'Unknown')}")
            continue
            
        # Clean path formatting mapping anchor matching the git_sync utility
        rel_path = file_info["file_path"].replace("\\", "/")
        
        # If the script includes 'src/' prefix, strip it so it matches your repo database layout
        if rel_path.startswith("src/"):
            rel_path = rel_path[4:]
            
        print(f"📦 Processing file module: {rel_path}")
        db.sync_file_node(rel_path, file_info["file_hash"])
        
        # Combine both functions and classes to capture frontend and backend structures
        all_structural_blocks = file_info.get("functions", []) + file_info.get("classes", [])

        for func in all_structural_blocks:
            func_name = func.get("name", "anonymous")
            func_body = func.get("body", "")
            
            if not func_body:
                continue
                
            print(f"   └── Extracting chunk structure: {func_name}")
            
            # --- FIX: Call our updated multi-vector chunking embedding engine ---
            vector_chunks = embedder.get_embeddings_for_piece(func_body)
            
            if len(vector_chunks) > 1:
                print(f"       📦 Splitting massive component into {len(vector_chunks)} search chunks.")
            
            # --- FIX: Commit full chunked layers securely to the database ---
            db.sync_chunked_method_data(
                file_path=rel_path,
                method_name=func_name,
                method_data=func,
                vector_chunks=vector_chunks
            )
            
    db.close()
    print("✨ Full multi-language codebase ingestion complete!")

if __name__ == "__main__":
    current_directory = os.path.join(get_git_root(os.curdir), "src")
    run_ingestion(current_directory)
