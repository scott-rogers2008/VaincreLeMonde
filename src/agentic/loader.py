###
### loader.py -- loads all of the md files into neo4j graphs preperatory for other agents to use it as a graphRAG
###      it uses chunk_agent.py to break up the md files into semantic chunks to help facilitate vector searches
###      and utils has (or will have) useful utilities like get_git_root(<path>) to help find all the files to be loaded.
###

import os
from langchain_neo4j import Neo4jGraph
from utils import get_git_root

os_walk_exclude = {'.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', '.vs',  '.vscode', 'node_modules'}

class MDFileChangeHandler:
    def __init__(self, agent_module_path):
        self.agent_module_path = agent_module_path

    def sync_all(self):
        base_dir = get_git_root(os.curdir)
        for root, dirs, files in os.walk(base_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in os_walk_exclude]
            for file in files:
                if ".aider" in file:
                    continue
                if file.endswith('.md'):
                    md_file_path = os.path.join(root, file)
                    print(f"Processing {md_file_path}")
                    self.process_md_file(md_file_path)

    def process_md_file(self, md_file_path):
        # Import the necessary functions from the agent module
        import importlib.util
        spec = importlib.util.spec_from_file_location("agent_module", self.agent_module_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        # Read the content of the .md file
        with open(md_file_path, 'r', encoding='utf-8') as f:
            document_text = f.read()

        # Import metadata from folder name
        metadata = {
            "source": "local",
            "title": md_file_path,
            "author": "Unknown",
            "type": os.path.basename(os.path.dirname(md_file_path))
        }

        # Call the semantic_chunking and neo4j_nodes_and_relations functions
        chunks, _ = agent_module.init_chunkrag_pipeline(document_text)
        graph = Neo4jGraph(url=os.environ.get("NEO4J_URL"), username=os.environ.get("NEO4J_USERNAME"), password=os.environ.get("NEO4J_PASSWORD"))
        agent_module.neo4j_nodes_and_relations(graph, chunks, metadata)

if __name__ == "__main__":
    # Define the path to the agent module
    agent_module_path = 'src/agentic/chunk_agent.py'

    # Create an instance of MDFileChangeHandler and pass it the agent module path
    md_file_change_handler = MDFileChangeHandler(agent_module_path)

    # Sync all .md files in the repository root
    md_file_change_handler.sync_all()
