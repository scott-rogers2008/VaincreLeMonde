import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.agentic.utils import get_git_root

class MDFileChangeHandler(FileSystemEventHandler):
    def __init__(self, agent_module_path, base_dir):
        self.agent_module_path = agent_module_path
        self.base_dir = base_dir

    def on_modified(self, event):
        if event.is_directory:
            return
        elif event.src_path.endswith('.md'):
            print(f"Detected change in {event.src_path}")
            self.process_md_file(event.src_path)

    def process_md_file(self, md_file_path):
        # Import the necessary functions from the agent module
        import importlib.util
        spec = importlib.util.spec_from_file_location("agent_module", self.agent_module_path)
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)

        # Read the content of the .md file
        with open(md_file_path, 'r', encoding='utf-8') as f:
            document_text = f.read()

        # Call the semantic_chunking and neo4j_nodes_and_relations functions
        metadata = {
            "source": "local",
            "title": os.path.basename(md_file_path).split('.')[0],
            "author": "Unknown",
            "type": "Text"
        }
        chunks, _ = agent_module.init_chunkrag_pipeline(document_text)
        graph = Neo4jGraph(url=os.environ.get("NEO4J_URL"), username=os.environ.get("NEO4J_USERNAME"), password=os.environ.get("NEO4J_PASSWORD"))
        agent_module.neo4j_nodes_and_relations(graph, chunks, metadata)

if __name__ == "__main__":
    # Define the path to the agent module
    agent_module_path = 'src\agentic\chunk_agent.py'
    base_dir = get_git_root()

    # Create an instance of the MDFileChangeHandler and pass it the agent module path and base directory
    event_handler = MDFileChangeHandler(agent_module_path, base_dir)

    # Set up the observer with the event handler
    observer = Observer()
    observer.schedule(event_handler, base_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
