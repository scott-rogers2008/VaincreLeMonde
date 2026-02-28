###
### loader.py -- loads all of the md files into neo4j graphs preperatory for other agents to use it as a graphRAG
###      it uses chunk_agent.py to break up the md files into semantic chunks to help facilitate vector searches
###      and utils has (or will have) useful utilities like get_git_root(<path>) to help find all the files to be loaded.
###

import os
from langchain_neo4j import Neo4jGraph
from utils import get_git_root

os_walk_exclude = {'.aider.tags.cache.v4', '.git', '.wenv', '.wvenv', '.venv', '.vs',  '.vscode', 'node_modules', 'src'}
# Note that 'src' is only a temporary exclution, since there aren't any documents beyond that point that I'm ready to include

# Get neo4j credentials from environment variables
url=os.environ.get("NEO4J_URL")
username=os.environ.get("NEO4J_USERNAME")
password=os.environ.get("NEO4J_PASSWORD")

class MDFileChangeHandler:
    def __init__(self, agent_module_path):
        self.agent_module_path = agent_module_path

    def sync_all(self):
        base_dir = get_git_root(os.curdir)
        graph = Neo4jGraph(url=url, username=username, password=password)

        for root, dirs, files in os.walk(base_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in os_walk_exclude]

            # 1. Create the Directory Backbone
            for d in dirs:
                dir_path = os.path.join(root, d)
                parent_path = root
                
                # Cypher to link folder to its parent
                query = """
                MERGE (p:Directory {path: $parent_path})
                MERGE (c:Directory {path: $child_path})
                SET c.name = $name
                MERGE (c)-[:CHILD_OF]->(p)
                """
                graph.query(query, {
                    "parent_path": parent_path, 
                    "child_path": dir_path, 
                    "name": d
                })

            for file in files:
                if ".aider" in file:
                    continue
                if file.endswith('.md'):
                    md_file_path = os.path.join(root, file)
                    print(f"Processing {md_file_path}")
                    self.process_md_file(md_file_path, graph, root)

    def process_md_file(self, md_file_path, graph, parent_path):
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
            "source": "https://github.com/scott-rogers2008/VaincreLeMonde/",
            "path": parent_path,
            "title": md_file_path,
            "author": "Unknown",
            "type": os.path.basename(os.path.dirname(md_file_path))
        }

        # Call the semantic_chunking and neo4j_nodes_and_relations functions
        chunks, _ = agent_module.init_chunkrag_pipeline(document_text)
        graph = Neo4jGraph(url=url, username=username, password=password)
        agent_module.neo4j_nodes_and_relations(graph, chunks, metadata)

        # Link the Directory to the File created by the agent
        # We use MERGE on both to ensure we don't duplicate, 
        # but the Directory should already exist from sync_all.
        link_query = """
        MATCH (d:Directory {path: $parent_path})
        MATCH (f:Document {source: $source, title: $file_path})
        MERGE (f)-[:CHILD_OF]->(d)
        """
        graph.query(link_query, {
            "parent_path": parent_path, 
            "source": "https://github.com/scott-rogers2008/VaincreLeMonde/",
            "file_path": md_file_path
        })

if __name__ == "__main__":
    # Define the path to the agent module
    agent_module_path = 'src/agentic/chunk_agent.py'

    # Create an instance of MDFileChangeHandler and pass it the agent module path
    md_file_change_handler = MDFileChangeHandler(agent_module_path)

    # Sync all .md files in the repository root
    md_file_change_handler.sync_all()
