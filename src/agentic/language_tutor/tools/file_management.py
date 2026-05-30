# tools/file_management.py
import os
from smolagents import tool
from markdown_it import MarkdownIt
from .utils import get_git_root

import os
from smolagents import tool

import os
from smolagents import tool

@tool
def directory_explorer(path: str) -> str:
    """
    Lists the contents of a directory.
    Args:
        path: The path (relative to references/) to explore.
    """
    try:
        # 1. Force the base to your project root
        base_dir = get_git_root(os.curdir)
        ref_dir_name = "references"
        ref_dir_path = os.path.abspath(os.path.join(base_dir, ref_dir_name))
        
        # 2. Clean the input path
        # Normalize slashes (converts / to \ on Windows)
        normalized_path = os.path.normpath(path.lstrip("/\\"))
        
        # 3. If agent included 'references' in the string, strip it manually
        if normalized_path.startswith(ref_dir_name):
            # Remove 'references' plus the following separator
            clean_path = normalized_path[len(ref_dir_name):].lstrip(os.sep)
        else:
            clean_path = normalized_path

        # 4. Final target construction
        target_path = os.path.abspath(os.path.join(ref_dir_path, clean_path))

        # Security check: Ensure we are still inside references/
        if not target_path.startswith(ref_dir_path):
            return f"Error: Access denied. Path must be inside '{ref_dir_name}/'."

        if not os.path.exists(target_path):
            # Debug info helps the agent correct its mistake
            return f"Error: Path '{target_path}' not found. Current dir: {os.getcwd()}"
            
        if not os.path.isdir(target_path):
            return f"Error: '{path}' is a file. Listing aborted."

        # 5. List and format
        items = sorted(os.listdir(target_path))
        output = []
        for i in items:
            prefix = "[DIR] " if os.path.isdir(os.path.join(target_path, i)) else "[FILE]"
            output.append(f"{prefix} {i}")
        
        return "\n".join(output) if output else "Directory is empty."

    except Exception as e:
        return f"Error: {str(e)}"

@tool
def read_markdown_content(file_path: str) -> str:
    """Reads a .md file from the references directory.
    
    Args:
        file_path: The path to the .md file to be read relative to references/.
    """
    try:
        # Use the same logic as directory_explorer
        base_dir = os.getcwd()
        ref_dir_path = os.path.abspath(os.path.join(base_dir, "references"))
        
        # Clean path (strips 'references' if the agent included it)
        clean_path = file_path.replace("references", "").lstrip("/\\")
        full_path = os.path.join(ref_dir_path, clean_path)

        if not os.path.exists(full_path):
            return f"Error: File not found at {full_path}"

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Simplified extraction to ensure you actually get text
        md = MarkdownIt()
        tokens = md.parse(content)
        # Better fallback: if parsing logic is too strict, you get nothing
        text = " ".join([t.content for t in tokens if t.content]).strip()
        
        return text if text else content[:500] # Return raw content if parser yields nothing
    except Exception as e:
        return f"Error reading markdown file: {str(e)}"
    
@tool
def manage_directory(path: str, create: bool = False) -> str:
    """
    Checks if a directory exists and can create it if requested.
    Args:
        path: The relative path within references (e.g., 'speeches/new_category').
        create: Set to True ONLY if the user has explicitly given permission to create this folder.
    """
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
    
    return f"PROMPT REQUIRED: The directory '{path}' does not exist. Do you want to create it? Please reply with 'yes' to proceed."

