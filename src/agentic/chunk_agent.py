import requests
import nltk
import os
from bs4 import BeautifulSoup as bs
from sentence_transformers import SentenceTransformer, util
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_community.vectorstores import Neo4jVector
from langchain_community.docstore.document import Document
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.tools import Tool

# Set up Neo4j credentials
neo4j_url = "neo4j://192.168.13.1:7687"
username = "neo4j"
password = "password"

base_dir = os.environ.get("BASE_DIR")
if not base_dir or len(base_dir) == 0:
    base_dir = "D:/VaincreLeMonde"

# --- Step 1: Semantic Chunking ---
def to_boolean(llm_response):
    cleaned_response = llm_response.strip().lower()
    if cleaned_response.find('no') != -1:
        return False
    elif cleaned_response.find('yes') != -1:
        return True
    else:
        # Handle cases where the response is ambiguous or off-topic
        raise ValueError(f"Could not determine a boolean value from the LLM response '{llm_response}'.")


def llm_check_semantic_break(pre_sentence, post_sentence, llm):
    template = """
    You are a relevance evaluator. Your task is to determine if there is logical break in semantics given two sections and only answer with a "yes" or a "no".
   
    Query: Based on the provided text, Is there a clear change in theme or all of the following: a new physical location, a notable passage of time, or a switching of characters occur here and are either of the sections small on their own (i.e. only one sentence long)? Answer "yes" or "no".
    section1: {section1}
    section2: {section2}
    """
    valid_resp = False
    resp = False
    while not valid_resp:
        prompt = PromptTemplate(template=template, input_variables=["section1", "section2"])
        llm_chain = (
            prompt  # Apply the prompt template
            | llm  # Use the language model to answer the question based on context
            | StrOutputParser()  # Parse the model's response as a string
        )
        response = llm_chain.invoke({"section1":pre_sentence, "section2":post_sentence})
        try:
            resp = to_boolean(response)
            valid_resp = True
        except LookupError as e:  # Corrected typo from 'LookoupError' to 'LookupError'
            print(f"{e} -- trying again...")
            valid_resp = False


    return resp


def semantic_chunking(document, llm, model_name='all-MiniLM-L6-v2', threshold=0.4):
    """
    Chunks a document into semantically coherent sections.
    """
    # Tokenize the document into paragraphs
    paragraphs_unfilt = document.split('\n')
    paragraphs = [item for item in paragraphs_unfilt if item] #remove empty
   
    # Load a pre-trained embedding model
    model = SentenceTransformer(model_name)
    sentence_embeddings = model.encode(paragraphs, convert_to_tensor=True)
   
    # Calculate cosine similarity between consecutive paragraphs
    cosine_similarities = []
    for i in range(len(paragraphs) - 1):
        cosine_similarities.append(util.cos_sim(sentence_embeddings[i], sentence_embeddings[i+1]))
   
    # Identify chunk boundaries where similarity drops below the threshold
    chunks = []
    current_chunk = [paragraphs[0]]
    for i in range(len(paragraphs) - 1):
        if cosine_similarities[i].item() < threshold and llm_check_semantic_break(current_chunk, paragraphs[i+1], llm):
            # End the current chunk and start a new one
            chunks.append("\n".join(current_chunk))
            current_chunk = [paragraphs[i+1]]
        else:
            current_chunk.append(paragraphs[i+1])
    chunks.append("\n".join(current_chunk)) # Add the last chunk
   
    print(f"{len(chunks)} - chunks detected from {len(paragraphs)} paragraphs")
    return chunks


def graph_details(llm, graph, chunks, text_summary):
    """
    Filters chunks based on relevance to the query using an LLM.
    """


    # Prompt template for relevance assessment
    template = """
    You analyze text to descover why the author chose to write a given scene. Given the summary of
    the whole text and the chunk of text for the given scene, what is the purpose of this chunk?
   
    Text Summary: {text_summary}
    Scene: {chunk}
    Summary:
    """


    prompt = PromptTemplate(template=template, input_variables=["text_summary", "chunk"])


    llm_chain = (
        prompt  # Apply the prompt template
        | llm  # Use the language model to answer the question based on context
        | StrOutputParser()  # Parse the model's response as a string
    )


    for chunk in chunks:
        # Get the relevance score from the LLM
        response = llm_chain.invoke({"text_summary":text_summary, "chunk":chunk})
        try:
            graph.query(nquery, params={"summary":response})
            graph.query(rquery, params={"text":chunk, "summary":response})
        except ValueError:
            print(f"Could not find relevance score for chunk: {chunk} got response {response}")




def neo4j_nodes_and_relations(graph, chunks, metadata):
    docs = []
    seq = 0
    for chunk in chunks:
        metadata["chunk_id"] = seq
        docs.append(Document(page_content=chunk, metadata=metadata))
        seq += 1
       
    # Create the embedder instance
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Create or connect to Neo4jVector store
    neo4j_vector = Neo4jVector.from_documents(
        embedding=embeddings,
        documents=docs,
        url=neo4j_url,
        username=username,
        password=password,
        index_name="vector_index", # Optional: specify index name
    )


    # Now connect each of these chunks to gether and to a new node called Document
    nquery = """
    CREATE (n:Document {title: $title, author: $author, source: $source})
    RETURN n
    """
    graph.query(nquery, params={"title":metadata["title"],
                                "author":metadata["author"],
                                "source": metadata["source"]})
    nquery = """
    MATCH (a:Chunk {chunk_id: $seq, source: $source}), (b:Chunk {chunk_id: $next, source: $source})
    CREATE (a)-[:NEXT_CHUNK]->(b)
    RETURN a, b
    """
    dquery = """
    MATCH (a:Chunk {chunk_id: $seq, source: $source}), (b:Document {source: $source})
    CREATE (a)-[:FROM_DOCUMENT]->(b)
    RETURN a, b
    """
    for i in range(len(chunks) - 1):
        graph.query(nquery, params={"seq":i, "source":metadata["source"], "next":i+1})
        graph.query(dquery, params={"seq":i, "source":metadata["source"]})

    graph.query(dquery, params={"seq":len(chunks)-1, "source":metadata["source"]})


    return neo4j_vector


def init_from_existing(llm_model="glm4-tool:9b"):
    print("--- Starting ChunkRAG Pipeline ---")
   
    # Initialize the LLM (e.g., using OllamaLLM for a local model)
    ollama_llm = ChatOllama(model=llm_model)


    # Create the embedder instance
    embeddings = OllamaEmbeddings(model="nomic-embed-text")


    # Create or connect to Neo4jVector store
    neo4j_vector = Neo4jVector.from_existing_index(
        embedding=embeddings,
        url=neo4j_url,
        username=username,
        password=password,
        index_name="vector_index", # Optional: specify index name
    )
   
    return ollama_llm, neo4j_vector


# --- Main RAG Pipeline ---
def init_chunkrag_pipeline(document, llm_model="glm4-tool:9b"):
    """
    Implements the ChunkRAG pipeline.
    """


    # Initialize the LLM (e.g., using OllamaLLM for a local model)
    ollama_llm = ChatOllama(model=llm_model)


    # 1. Semantic Chunking
    print("Step 1: Performing semantic chunking...")
    chunks = semantic_chunking(document, ollama_llm)
    print(f"Document split into {len(chunks)} chunks.")
    return chunks, ollama_llm


def query_chunkrag_pipeline(neo4j_vector, ollama_llm, graph, query):
    # 1. Create the Vector Search Tool
    vector_search_tool = Tool(
        name="Vector_Search",
        func=neo4j_vector.as_retriever().invoke,
        description="You are able to analyze text that has been chunked for easier access and utilize the metadata associated with it."
    )


    # 2. Create the Cypher (Graph) Tool
    cypher_chain = GraphCypherQAChain.from_llm(
        cypher_llm=ollama_llm,
        qa_llm=ollama_llm,
        graph=graph,
        allow_dangerous_requests=True,
        verbose=True
    )
    cypher_search_tool = Tool(
        name="Graph_Search",
        func=cypher_chain.run,
        description="Answer basic questions."
    )


    # List of tools for the agent
    tools = [vector_search_tool, cypher_search_tool]


    # Define the agent's prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
         You are an AI assistant who analyzes documents by accessing individual chunks with
         their associated metadata. Use chunk_id to determine order of the chunks from the
         original document.
         """),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])


    # Create and run the agent
    llm_with_tools = ollama_llm.bind_tools(tools)
    agent = create_tool_calling_agent(llm_with_tools, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    response = agent_executor.invoke({"input": query})
    return response


# --- Example Usage ---
if __name__ == "__main__":
    
    with open(f"{base_dir}/training/GnosticUniversalism/README.md", encoding="utf-8") as f:
        document_text = f.read()
    metadata = {"source": "local",
                "title": "Foundational Understanding",
                "author":  "Scott Rogers",
                "type": "inspirational, philosophy"}
   
    # User sample query
    user_query = "What is the most important thing to learn?"
    graph = Neo4jGraph(url=neo4j_url, username=username, password=password)
   
    # Run the pipeline
    nquery ="""
    MATCH (n:Document {source: $source})
    RETURN n
    """
    result = graph.query(nquery, params={"source":metadata["source"]})
    if len(result) == 0:
        chunks, llm = init_chunkrag_pipeline(document_text)
        # Fill out graph
        neo4j_vector = neo4j_nodes_and_relations(graph, chunks, metadata)
    else:
        llm, neo4j_vector = init_from_existing()
   


    final_response = query_chunkrag_pipeline(neo4j_vector, llm, graph, user_query)
    print("\n--- Final Answer ---")
    print(final_response["output"])
