from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_community.vectorstores import Neo4jVector
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit, FileManagementToolkit
from langchain_community.tools.playwright.utils import create_sync_playwright_browser, create_async_playwright_browser
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_classic.tools import Tool
import langchain
langchain.verbose = True

import os
import nest_asyncio
nest_asyncio.apply()

# Set up Neo4j credentials from environment variables
neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

model = ChatOllama(model="llama3.1")
search = DuckDuckGoSearchRun()
syncBrowser = create_sync_playwright_browser()
asyncBrowser = create_async_playwright_browser()
toolkit = PlayWrightBrowserToolkit.from_browser(sync_browser=syncBrowser)
tools = toolkit.get_tools()
tools_by_name = {tool.name: tool for tool in tools}
browser = tools_by_name["navigate_browser"]
extract = tools_by_name["extract_text"]

localdir = os.path.join(os.path.curdir, "dds_files")
ftoolkit = FileManagementToolkit(root_dir=localdir)
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

def debug_vector_search(query):
    print(f"\n--- DEBUG: Vector Search Query: {query} ---")
    results = neo4j_vector.as_retriever().invoke(query)
    
    # Print what was found so YOU can see it
    if not results:
        print("--- DEBUG: No results found in Vector Index! ---")
    for i, res in enumerate(results):
        print(f"Result {i+1}: {res.page_content[:200]}...") # Print first 200 chars
        
    return results

vector_search_tool = Tool(
    name="Vector_Search",
    func=debug_vector_search, # Use our new wrapper
    description="Primary tool for accessing the knowledge base chunks."
)


# 2. Create the Cypher (Graph) Tool
graph = Neo4jGraph(url=neo4j_url, username=username, password=password)

cypher_chain = GraphCypherQAChain.from_llm(
    cypher_llm=model,
    qa_llm=model,
    graph=graph,
    allow_dangerous_requests=True,
    verbose=True
)

cypher_search_tool = Tool(
    name="Graph_Search",
    func=cypher_chain.run,
    description="Answer questions based on knowledge graph aquired so far."
)

chathistory = InMemoryChatMessageHistory()

all_tools = [vector_search_tool, cypher_search_tool]
model_with_tools = model.bind_tools(all_tools)

prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a knowledge base that lets the user interact with the documents contianed through the Vector_Search and "
        "Graph_Search tools. ... Always start with Vector_Search even for ambiguous questions, and only ask for clarification "
        "**after** retrieving partial results.."),
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
            "chat_history":chathistory.messages
        })
        print("{Result}:\n",result['output'])
        chathistory.add_user_message(prompt)
        chathistory.add_ai_message(result['output'])
    except KeyboardInterrupt:
        print("Stopping on interupt.")
        break
