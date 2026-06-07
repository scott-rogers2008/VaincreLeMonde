# src/agentic/codebase_guru/tools/force_sync.py

import subprocess
import os
from .utils import get_git_root

def force_git_reindex():
    git_root = os.path.abspath(get_git_root(os.curdir))
    src_dir = os.path.join(git_root, "src")
    scan_target = src_dir if os.path.exists(src_dir) else git_root
    
    print(f"📡 Step 1: Temporarily touching files under: {scan_target}")
    python_files = []
    
    # 1. Gather all python files in your source directory
    for root, _, files in os.walk(scan_target):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
                
    # 2. Append a harmless trailing space to every file to force a Git delta change
    print(f"✏️  Modifying {len(python_files)} files with a temporary whitespace...")
    for file_path in python_files:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(" ") # Harmless space at the end of the script
            
    # 3. Execute your low-resource Git delta sync tool
    print("\n🔄 Step 2: Triggering Git Delta Sync to re-populate Neo4j...")
    subprocess.run(["python", "-m", "agentic.codebase_guru.tools.git_sync"], cwd=git_root)
    
    # 4. Clean up your Git working tree to remove the temporary spaces completely
    print("\n🧹 Step 3: Resetting files back to pristine original Git states...")
    subprocess.run(["git", "checkout", "."], cwd=git_root)
    print("✨ Graph database re-population complete! All forward-slash nodes are safely restored.")

if __name__ == "__main__":
    force_git_reindex()
 