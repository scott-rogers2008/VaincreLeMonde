from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_community.vectorstores import Neo4jVector
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit, FileManagementToolkit
from langchain_community.tools.playwright.utils import create_sync_playwright_browser, create_async_playwright_browser
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_postgres  import PostgresChatMessageHistory
from langchain_classic.tools import tool
import langchain
langchain.verbose = True

from utils import get_git_root
import os
import uuid
import psycopg
import nest_asyncio
nest_asyncio.apply()

base_dir = get_git_root(os.curdir)

# Set up Neo4j credentials from environment variables
neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

psql_user = os.environ.get("PSQL_USER")
psql_pswq = os.environ.get("PSQL_PASSWORD")

model = ChatOllama(model="llama3.1")
search = DuckDuckGoSearchRun()
syncBrowser = create_sync_playwright_browser()
asyncBrowser = create_async_playwright_browser()
toolkit = PlayWrightBrowserToolkit.from_browser(sync_browser=syncBrowser)
tools = toolkit.get_tools()
tools_by_name = {tool.name: tool for tool in tools}
browser = tools_by_name["navigate_browser"]
extract = tools_by_name["extract_text"]

# localdir = os.path.join(os.path.curdir, "dds_files")
ftoolkit = FileManagementToolkit(root_dir=base_dir)
ftools = ftoolkit.get_tools()
ftools_by_name = {tool.name: tool for tool in ftools}
fread = ftools_by_name["read_file"]
fwrite = ftools_by_name["write_file"]
list_directory = ftools_by_name['list_directory']

# Create the embedder instance
embeddings = OllamaEmbeddings(model="nomic-embed-text")

neo4j_vector = Neo4jVector.from_existing_index(
    embedding= embeddings,
    url= neo4j_url,
    username = username,
    password = password, 
    index_name="vector_index",
    text_node_property="text"
)

@tool("Vector_Search")
def vector_search_tool(query: str):
    """Primary tool for accessing the knowledge base chunks. 
    Pass only a single search query string here."""
    print(f"\n--- DEBUG: Vector Search Query: {query} ---")
    results = neo4j_vector.as_retriever().invoke(query)
    
    if not results:
        print("--- DEBUG: No results found in Vector Index! ---")
    for i, res in enumerate(results):
        print(f"Result {i+1}: {res.page_content[:200]}...")
    return results


# 2. Create the Cypher (Graph) Tool
graph = Neo4jGraph(url=neo4j_url, username=username, password=password)

cypher_chain = GraphCypherQAChain.from_llm(
    cypher_llm=model,
    qa_llm=model,
    graph=graph,
    allow_dangerous_requests=True,
    verbose=True
)

@tool("Graph_Search")
def graph_search_tool(query: str):
    """Answer questions based on the knowledge graph acquired so far.
    Input should be a natural language question string."""
    return cypher_chain.invoke(query)

@tool("Get_Graph_Schema")
def get_graph_schema(_: str = ""):
    """
    Returns the current schema of the Neo4j database. 
    Use this to see existing node labels, properties, and relationships 
    before suggesting how to connect new documents.
    """
    # graph is the Neo4jGraph object already defined in your script
    return graph.get_schema

# chathistory = InMemoryChatMessageHistory()
### switch to longterm postgress based memory
conn_info = f"postgresql://{psql_user}:{psql_pswq}@localhost:5432/{psql_user}"
sync_connection = psycopg.connect(conninfo=conn_info)
table_name = "chat_history"
session_id = "user_session_001"
session_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, session_id))
chat_history = PostgresChatMessageHistory(
    table_name,
    session_uuid,
    sync_connection= sync_connection,
)
chat_history.create_tables(sync_connection, table_name)

@tool("Clear_History")
def clear_history():
    """
    Clears all of the chat history.
    """
    chat_history.clear()

all_tools = [vector_search_tool, graph_search_tool, get_graph_schema, clear_history, fread, list_directory]
model_with_tools = model.bind_tools(all_tools)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a knowledge assistant and graph architect. "
     "1. Use Vector_Search to find document content.\n"
     "2. Use Get_Graph_Schema to see how the database is currently structured.\n"
     "3. When asked for connection advice, suggest specific Node labels and Relationship types "
     "(e.g., 'Link Document A to Entity B via a :MENTIONS relationship') to improve searchability."
     "You also have access to the documents directly through list_directory and read_file with"
     f"your root directory being {base_dir}."),
    ("placeholder", "{chat_history}"),
    ("user", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(
    llm=model_with_tools, 
    tools=all_tools, 
    prompt=prompt_template
)

executor = AgentExecutor(
    name="Multifaceted Agent",
    agent=agent, 
    tools=all_tools, 
    verbose=True
)

while True:
    try:
        prompt = input(">:::> ")
        if prompt in ["quit", "exit"]:
            break
        result = executor.invoke({
            "input":prompt,
            "chat_history":chat_history.messages
        })
        print("{Result}:\n",result['output'])
        chat_history.add_user_message(prompt)
        chat_history.add_ai_message(result['output'])
    except KeyboardInterrupt:
        print("Stopping on interupt.")
        break
