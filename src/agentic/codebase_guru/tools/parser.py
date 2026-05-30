import ast
import hashlib
import json  # FIX 1: Added missing json import
import os
import subprocess

os_walk_exclude = {
    '.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', 
    '.vs', '.angular', '.vscode', 'node_modules', "angular",
    'dist', 'browser', 'out', 'build'
}
class CodebaseParser:
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def calculate_hash(self, text: str) -> str:
        """Generates a unique signature to detect code/doc changes."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def extract_comments_manually(self, file_path: str) -> list:
        """Extracts standalone comments (# or //) and tracking line numbers."""
        comments = []
        is_js_ts = file_path.endswith(('.js', '.ts', '.jsx', '.tsx'))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='cp1252', errors='replace') as f:
                lines = f.readlines()

        for line_idx, line in enumerate(lines, 1):
            clean_line = line.strip()
            # FIX 4: Support both Python and JavaScript comment tokens
            if not is_js_ts and clean_line.startswith('#'):
                comments.append({
                    "text": clean_line.lstrip('# ').strip(),
                    "line_number": line_idx,
                    "hash": self.calculate_hash(clean_line)
                })
            elif is_js_ts and clean_line.startswith('//'):
                comments.append({
                    "text": clean_line.lstrip('/ ').strip(),
                    "line_number": line_idx,
                    "hash": self.calculate_hash(clean_line)
                })
        return comments

    def parse_file(self, file_path: str) -> dict:
        """Dissects a file into structural nodes and documentation."""
        relative_path = os.path.relpath(file_path, self.root_dir)
        
        # FIX 2: Handle JavaScript / TypeScript completely separate from Python AST
        if file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='cp1252', errors='replace') as f:
                    source_code = f.read()

            file_hash = self.calculate_hash(source_code)

            agent_script = os.path.join(self.root_dir, "frontend", "src", "agents", "jsparser.js")
            result = subprocess.run(
                ['node', agent_script, file_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                try:
                    js_data = json.loads(result.stdout)
                    # Merge basic file info with what our JS node agent found
                    js_data["file_path"] = relative_path
                    js_data["file_hash"] = file_hash
                    js_data["comments"] = self.extract_comments_manually(file_path)
                    return js_data
                except json.JSONDecodeError:
                    print(f"❌ Failed to decode JS Agent response for {relative_path}")
                    return {"file_path": relative_path, "error": "Invalid JSON from JS agent"}
            else:
                print(f"JS Agent Runtime Error: {result.stderr}")
                return {"file_path": relative_path, "error": "JS Agent failed"}

        # --- Python Processing Flow ---
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='cp1252', errors='replace') as f:
                source_code = f.read()

        file_hash = self.calculate_hash(source_code)
        file_data = {
            "file_path": relative_path,
            "file_hash": file_hash,
            "classes": [],
            "functions": [],
            "comments": self.extract_comments_manually(file_path)
        }

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            print(f"⚠️ Syntax error parsing file: {relative_path}. Skipping AST extraction.")
            return file_data

        # Traverse the Abstract Syntax Tree for Python
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                class_body = ast.unparse(node)
                file_data["classes"].append({
                    "name": node.name,
                    "docstring": docstring,
                    "doc_hash": self.calculate_hash(docstring) if docstring else "",
                    "body": class_body,
                    "body_hash": self.calculate_hash(class_body)
                })
            elif isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                func_body = ast.unparse(node)
                file_data["functions"].append({
                    "name": node.name,
                    "docstring": docstring,
                    "doc_hash": self.calculate_hash(docstring) if docstring else "",
                    "body": func_body,
                    "body_hash": self.calculate_hash(func_body)
                })
        return file_data

    def scan_codebase(self) -> list:
        """Walks the directory tree looking for python and frontend files."""
        parsed_codebase = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in os_walk_exclude]
            for file in files:
                if file.startswith(".") or "node_modules" in file:
                    continue
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                    full_path = os.path.join(root, file)
                    parsed_codebase.append(self.parse_file(full_path))
        return parsed_codebase


if __name__ == "__main__":
    parser = CodebaseParser(root_dir=".")
    sample_data = parser.scan_codebase()
    print(json.dumps(sample_data[:3], indent=2))
