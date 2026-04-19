# tools/file_management.py
import os
from smolagents import tool
from markdown_it import MarkdownIt
from .utils import get_git_root

@tool
def directory_explorer() -> str:
    """
    Returns a visual tree of the 'references' directory to help decide where to save a file.
    Use this to see existing categories and subdirectories.
    """
    base_dir = get_git_root(os.curdir)
    base_references = os.path.abspath(os.path.join(base_dir, "references"))
    if not os.path.exists(base_references):
        return f"Error: Reference directory not found at {base_references}"
    
    tree_output = "Current Reference Library Structure:\n"
    for root, dirs, files in os.walk(base_references):
        # Calculate indentation based on depth from base_references
        level = root.replace(base_references, '').count(os.sep)
        indent = ' ' * 4 * level
        
        # Add the directory name
        dir_name = os.path.basename(root) or "references"
        tree_output += f"{indent}{dir_name}/\n"
        
        # Add the files within this directory
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            tree_output += f"{sub_indent}- {f}\n"
    return tree_output

@tool
def read_markdown_content(file_path: str) -> str:
    """
    Reads a .md file from the references directory and extracts plain text for analysis.
    Args:
        file_path: The full path to the .md file to be read.
    """
    try:
        base_dir = get_git_root(os.curdir)
        # This forces the agent's path to be absolute relative to your project root
        full_path = os.path.normpath(os.path.join(base_dir, file_path))

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use markdown-it-py to extract plain text only
        md = MarkdownIt()
        tokens = md.parse(content)
        
        # Extract text from tokens, ignoring markdown syntax
        plain_text_parts = []
        for token in tokens:
            if token.type == "inline":
                plain_text_parts.append(token.content)
            elif token.type in ["paragraph_open", "heading_open"]:
                plain_text_parts.append("\n")
                
        return " ".join(plain_text_parts).strip()
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

