import os
import ollama
import psycopg
import json
import uuid
from neo4j import GraphDatabase
from utils import get_git_root
from smolagents import CodeAgent, LiteLLMModel, tool
from smolagents.memory import TaskStep

EMBED_MODEL = "nomic-embed-text"

model = LiteLLMModel(
    model_id="ollama/llama3.1",
    api_base="http://localhost:11434"
)

neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")
driver = GraphDatabase.driver(neo4j_url, auth=(username, password))


psql_user = os.environ.get("PSQL_USER")
psql_pswq = os.environ.get("PSQL_PASSWORD")

base_dir = get_git_root(os.curdir)

@tool
def vector_search(query: str, document_name: str = None) -> str:
    """
    Primary tool for accessing the knowledge base chunks. 
    Performing a semantic search in the Neo4j vector index returning full metadata.
    Args:
        query: The search query string.
        document_name: Optional filename to isolate search to a specific document.
    """
    
    response = ollama.embed(
        model="nomic-embed-text",
        input=query
    )
    query_embedding = response['embeddings'][0]
    cypher_query = """
    CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
    YIELD node, score
    WHERE ($doc_name IS NULL OR node.title = $doc_name)
    RETURN properties(node) AS metadata, score
    """
    
    params = {
        "index_name": "vector_index", # Must match your existing index name
        "top_k": 5,
        "embedding": query_embedding,
        "doc_name": document_name
    }

    results_text = []
    with driver.session() as session:
        records = session.run(cypher_query, params)
        for record in records:
            meta = record["metadata"]
            score = record["score"]
            meta.pop('embedding', None) 
            results_text.append(f"[Score: {score:.4f}] Metadata: {meta}")

    if not results_text:
        return "No relevant documents found in the vector index."
        
    return "\n---\n".join(results_text)

@tool
def graph_search(query: str) -> str:
    """
    Executes a Cypher query against the Neo4j database. 
    Use this to fetch specific relationships or aggregate data.
    Args:
        query: The Cypher query string to execute.
    """
    with driver.session() as session:
        result = session.run(query)
        # Limit output to prevent context overflow
        return str([record.data() for record in result][:10])

@tool
def get_graph_schema() -> str:
    """Returns the current schema of the Neo4j database."""
    with driver.session() as session:
        schema = session.run("CALL apoc.meta.schema() YIELD value RETURN value").single()
        return str(schema["value"]) if schema else "Schema unavailable."

@tool
def list_directory() -> str:
    """Lists files in the current working directory."""
    return str(os.listdir(base_dir))

@tool
def read_file(file_path: str) -> str:
    """
    Reads a file from disk.
    Args:
        file_path: Path to the file.
    """
    with open(os.path.join(base_dir, file_path), 'r') as f:
        return f.read()

conn_info = f"postgresql://{psql_user}:{psql_pswq}@localhost:5432/{psql_user}"
conn = psycopg.connect(conninfo=conn_info)
session_id = "user_session_001"
session_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, session_id))

@tool
def get_history(num: int) -> str:
    """
    Fetches the last num queries and responses to and from the chat agent.

    Args:
        num: The number of past messages to return.
    Returns:
        A list of dictionaries with 'role' and 'content' keys.
        Example: [{"role": "human", "content": "..."}, {"role": "ai", "content": "..."}]
    """
    history = []
    with conn.cursor() as cur:
        # Assuming the standard 'message_store' schema or similar
        cur.execute(
            "SELECT message FROM chat_history WHERE session_id = %s ORDER BY id DESC LIMIT %s",
            (session_uuid, num * 2)
        )
        rows = cur.fetchall()
        for row in rows[::-1]:
                # Extracting your specific DB schema format
                m = row[0] 
                history.append({
                    "role": m.get('data').get('type'),
                    "content": m.get('data').get('content')
                })
    return history
    
def get_messages(session_uuid: str):
    """Fetches the last 5 messages for this session from the database."""
    with conn.cursor() as cur:
        # Assuming the standard 'message_store' schema or similar
        cur.execute(
            "SELECT message FROM chat_history WHERE session_id = %s ORDER BY id DESC LIMIT 5",
            (session_uuid,)
        )
        rows = cur.fetchall()
        return [row[0] for row in rows][::-1]

def save_message(session_uuid: str, message_type: str, content: str, agent = None):
    """Saves a single message to the database."""
    tools_called =[]
    if agent != None:
        for step in agent.memory.steps:
            if hasattr(step, 'tool_calls') and step.tool_calls:
                for call in step.tool_calls:
                    tools_called.append({
                        "type": "tool_use",
                        "data": {
                            "tool_name": call.name,
                        }
                    })
    with conn.cursor() as cur:
        if agent != None:
            message_data = json.dumps({"data":{"type": message_type, "content": content, "tool_calls":tools_called}})
        else:
            message_data = json.dumps({"data":{"type": message_type, "content": content}})
        cur.execute(
            "INSERT INTO chat_history (session_id, message) VALUES (%s, %s)",
            (session_uuid, message_data)
        )
        conn.commit()

agent = CodeAgent(
    tools=[vector_search, graph_search, get_graph_schema, list_directory, read_file, get_history],
    model=model,
    additional_authorized_imports=["os", "json"] # Allows the agent to use these in code
)

system_prompt = (
    f"You are a knowledge assistant and graph architect. Your root directory is at {base_dir}. "
    "Use vector_search for content and get_graph_schema for structure. "
    "Suggest specific Node labels and Relationship types when asked for advice."
    "Load the files directly when you need to access all of the document."
)

past_messages = get_messages(session_uuid)
history_block = "\n".join([f"{m.get('data').get('type')}: {m.get('data').get('content')}" for m in past_messages])

if past_messages:
    seed_step = TaskStep(task=f"Load previous conversation history: {history_block}")
    # We set the 'log' or 'output' so it doesn't try to 'solve' this step
    seed_step.observations = "History loaded successfully. I will not use tools to re-examine these files."
    agent.memory.steps.append(seed_step)


# 5. Run Loop
while True:
    try:
        user_input = input(">:::> ")
        if user_input.lower() in ["quit", "exit"]:
            break
            
        result = agent.run(user_input, reset=False)
        
        save_message(session_uuid, "human", user_input)
        save_message(session_uuid, "ai", str(result), agent)
        
        print(f"{{Result}}:\n{result}")
        
    except KeyboardInterrupt:
        break
