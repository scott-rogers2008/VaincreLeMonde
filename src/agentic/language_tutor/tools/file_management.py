# src/agentic/language_tutor/tools/file_management.py
import os
from .utils import get_git_root

def directory_explorer(path: str) -> str:
    """Lists the contents of a target directory safely inside your references space."""
    try:
        base_dir = get_git_root(os.curdir)
        ref_dir_name = "references"
        ref_dir_path = os.path.abspath(os.path.join(base_dir, ref_dir_name))
        
        normalized_path = os.path.normpath(path.lstrip("/\\"))
        if normalized_path.startswith(ref_dir_name):
            clean_path = normalized_path[len(ref_dir_name):].lstrip(os.sep)
        else:
            clean_path = normalized_path
            
        target_path = os.path.abspath(os.path.join(ref_dir_path, clean_path))
        if not target_path.startswith(ref_dir_path):
            return f"Error: Access denied. Path must be inside '{ref_dir_name}/'."
            
        if not os.path.exists(target_path):
            return f"Error: Path '{target_path}' not found."
        if not os.path.isdir(target_path):
            return f"Error: '{path}' is a file. Listing aborted."
            
        items = sorted(os.listdir(target_path))
        output = []
        for i in items:
            prefix = "[DIR] " if os.path.isdir(os.path.join(target_path, i)) else "[FILE]"
            output.append(f"{prefix} {i}")
        return "\n".join(output) if output else "Directory is empty."
    except Exception as e:
        return f"Error: {str(e)}"

def read_markdown_content(file_path: str) -> str:
    """Reads a pristine text block from a local markdown document."""
    try:
        base_dir = os.getcwd()
        ref_dir_path = os.path.abspath(os.path.join(base_dir, "references"))
        clean_path = file_path.replace("references", "").lstrip("/\\")
        full_path = os.path.join(ref_dir_path, clean_path)
        
        if not os.path.exists(full_path):
            return f"Error: File not found at {full_path}"
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading markdown file: {str(e)}"

def manage_directory(path: str, create: bool = False) -> str:
    """Validates existence or allocates a missing directory layer."""
    base_refs = os.path.abspath(os.path.join(os.getcwd(), "..", "references"))
    target_dir = os.path.normpath(os.path.join(base_refs, path))
    if os.path.exists(target_dir):
        return f"Directory exists: {path}"
    if create:
        try:
            os.makedirs(target_dir, exist_ok=True)
            return f"Successfully created new directory: {path}"
        except Exception as e:
            return f"Failed to create directory: {str(e)}"
    return f"PROMPT REQUIRED: The directory '{path}' does not exist."
