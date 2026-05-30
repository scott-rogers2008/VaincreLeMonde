import os
from pathlib import Path
from tools.parser import CodebaseParser
from tools.embedder import LocalEmbedder
from tools.graph_db import CodebaseGraphManager
from utils import get_git_root

def run_ingestion(target_repo_path):
    print(f"🚀 Starting Codebase Guru ingestion for: {target_repo_path}")
    
    # 1. Initialize our custom tools
    parser = CodebaseParser(root_dir=target_repo_path)
    embedder = LocalEmbedder()
    db = CodebaseGraphManager()
    
    # Ensure indexes and constraints are active
    db.initialize_indexes()
    
    # 2. Parse the codebase files
    print("🔍 Scanning directories and building syntax tree...")
    parsed_files = parser.scan_codebase()
    
    # 3. Synchronize with Neo4j
    for file_info in parsed_files:
        if "error" in file_info or "file_hash" not in file_info:
            print(f"⏩ Skipping database sync for broken file: {file_info.get('file_path', 'Unknown')}")
            continue
        
        rel_path = file_info["file_path"].replace("\\", "/")
        if rel_path.startswith("src/"):
            rel_path = rel_path[4:]

        print(f"📦 Processing file: {rel_path}")
        db.sync_file_node(rel_path, file_info["file_hash"])
        
        # Ingest functions/methods found within the file
        for func in file_info["functions"]:
            print(f"   └── Extracting method: {func['name']}")
            
            # Generate local vector embeddings using Nomic
            body_vector = embedder.get_embedding(func["body"])
            doc_vector = embedder.get_embedding(func["docstring"]) if func["docstring"] else []
            
            # Commit to the graph database (manages history automatically)
            db.sync_method_and_docs(
                file_path=rel_path,
                method_data=func,
                body_vector=body_vector,
                doc_vector=doc_vector
            )
            
    db.close()
    print("✨ Codebase ingestion and history mapping complete!")

if __name__ == "__main__":
    # Test it out on this project folder to seed your database!
    current_directory  = os.path.join(get_git_root(os.curdir), "src")
    run_ingestion(current_directory)
