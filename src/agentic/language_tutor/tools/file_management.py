# src/agentic/language_tutor/tools/file_management.py
import os
from .utils import get_git_root
import logging

logger = logging.getLogger(__name__)

def _get_unified_references_path() -> str:
    """
    Internal helper to guarantee all file operations point to the exact same 
    absolute references directory at the repository root.
    """
    git_root = get_git_root(os.curdir)
    return os.path.abspath(os.path.join(git_root, "references"))

def save_markdown_document(content: str, filename: str, category_path: str) -> str:
    """
    Standardizes and resolves cross-platform file paths, ensures the target directory 
    tree exists, and commits the textual payload to disk using strict UTF-8 encoding.
    
    Returns:
        str: A clean, absolute, OS-normalized file path.
    """
    try:
        # FIX: Align base directory targeting around the repository git root
        ref_dir_path = _get_unified_references_path()
        
        # Sanitize and clean up inner subfolder path string noise
        clean_category = category_path.replace('\\', '/').strip('/')
        clean_filename = filename.replace('.md', '').strip() + '.md'
        
        # Resolve the path layout via native, absolute normalization loops
        target_dir = os.path.normpath(os.path.join(ref_dir_path, clean_category))
        os.makedirs(target_dir, exist_ok=True)
        
        full_absolute_path = os.path.normpath(os.path.join(target_dir, clean_filename))
        
        # Commit the structural document content cleanly to storage disk
        with open(full_absolute_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"✨ Document written safely to storage disk: {full_absolute_path}")
        return full_absolute_path

    except Exception as e:
        logger.error(f"Failed to execute file writing process pass: {str(e)}")
        raise IOError(f"File system management error during write phase: {str(e)}")
    
def directory_explorer(path: str) -> str:
    """Lists the contents of a target directory safely inside your references space."""
    try:
        ref_dir_path = _get_unified_references_path()
        
        normalized_path = os.path.normpath(path.lstrip("/\\"))
        if normalized_path.startswith("references"):
            clean_path = normalized_path[len("references"):].lstrip(os.sep)
        else:
            clean_path = normalized_path
            
        target_path = os.path.abspath(os.path.join(ref_dir_path, clean_path))
        if not target_path.startswith(ref_dir_path):
            return "Error: Access denied. Path must be inside 'references/'."
            
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
        # FIX: Align reading lookups directly with the same git-root base path
        ref_dir_path = _get_unified_references_path()
        
        # Handle cases where full absolute paths or relative fragments are passed in
        clean_path = file_path.replace("references", "").img_strip if hasattr(file_path, "img_strip") else file_path
        clean_path = str(clean_path).replace("\\", "/").lstrip("/ ")
        
        full_path = os.path.normpath(os.path.join(ref_dir_path, clean_path))
        
        if not os.path.exists(full_path):
            return f"Error: File not found at {full_path}"
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading markdown file: {str(e)}"

def manage_directory(path: str, create: bool = False) -> str:
    """Validates existence or allocates a missing directory layer."""
    # FIX: Clean up cross-cutting absolute parent paths to ensure reference consistency
    ref_dir_path = _get_unified_references_path()
    
    clean_path = path.replace("references", "").replace("\\", "/").lstrip("/ ")
    target_dir = os.path.normpath(os.path.join(ref_dir_path, clean_path))
    
    if os.path.exists(target_dir):
        return f"Directory exists: {path}"
    if create:
        try:
            os.makedirs(target_dir, exist_ok=True)
            return f"Successfully created new directory: {path}"
        except Exception as e:
            return f"Failed to create directory: {str(e)}"
    return f"PROMPT REQUIRED: The directory '{path}' does not exist."
