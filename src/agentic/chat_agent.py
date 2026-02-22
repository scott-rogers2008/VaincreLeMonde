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

import os
import nest_asyncio
nest_asyncio.apply()

# Set up Neo4j credentials from environment variables
neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

model = ChatOllama(model="glm4-tool:9b")
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

vector_search_tool = Tool(
    name="Vector_Search",
    func=neo4j_vector.as_retriever().invoke,
    description="You are able to analyze text that has been chunked for easier access and utilize the metadata associated with it."
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

agent = create_tool_calling_agent(
    llm=model, 
    tools=[vector_search_tool, cypher_search_tool, search, browser, extract, fread, fwrite, list_directory], 
    prompt=ChatPromptTemplate.from_messages([
        ("system", "Your a knowledge and learning expert with access to local knowledgebase of documents of what has been "
         "aquired so far about knowledge and learning as well as the chunks that these documents have been devided into through neo4j. "
         "You can also augment your knowledge by searching the internet and reading and writing to local text files. "
         ""
         "Think step-by-step:"
         "1. Use the the neo4j Graph_Search and Vector_Search tools to access aquired knowledge as a basis for responses"
         "2. Check the internet for aditional information that might be useful and or use other tools as required by the specific request."
         ""
         "First use the neo4j Vector_Search and Graph_Search to access aquired knowledge about knowledge and learning as a basis for responses."
         "Use the DuckDuckGo Search tool for searching the internet."
         "You can also extract information from the internet using the navigate_browser and extract_text tool."
         "Use the read_file tool to get the specifics from the file contents, don't rely on assumptions."
         "You can also use the list_directory to see what files you can access."),
        ("placeholder","{chat_history}"),
        ("human","{input}"),
        ("placeholder","{agent_scratchpad}"),
    ])
)

executor = AgentExecutor(
    name="Internet Agent",
    agent=agent, 
    tools=[search, browser, extract, fread, fwrite, list_directory], 
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
