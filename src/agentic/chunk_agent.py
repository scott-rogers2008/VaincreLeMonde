import requests
import nltk
import os
import numpy as np
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

from utils import get_git_root

MIN_CHUNK_CHARS = 400   # Don't split too early 
MAX_CHUNK_CHARS = 2000  # Safety valve (~500 tokens)

# Set up Neo4j credentials from environment variables
neo4j_url = os.environ.get("NEO4J_URL")
username = os.environ.get("NEO4J_USERNAME")
password = os.environ.get("NEO4J_PASSWORD")

base_dir = os.environ.get("BASE_DIR")
if not base_dir or len(base_dir) == 0:
    base_dir = get_git_root(os.curdir)

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
    # 1. Pre-check: Don't waste LLM time if the text is empty
    if not pre_sentence.strip() or not post_sentence.strip():
        return False

    template = """
        You are an expert document architect. Your task is to determine if Section 2 starts a 
        significantly different topic than Section 1.

        Section 1: {section1}
        Section 2: {section2}

        Think step-by-step:
        1. What is the primary theme of Section 1?
        2. What is the primary theme of Section 2?
        3. Is there a logical transition?

        If it's a new topic, say 'Decision: YES'. If it's a continuation, say 'Decision: NO'.
        """
    
    prompt = PromptTemplate(template=template, input_variables=["section1", "section2"])
    chain = prompt | llm | StrOutputParser()
    
    # Try a limited number of times to avoid infinite loops on your 3060
    for attempt in range(2):
        response = chain.invoke({"section1": pre_sentence, "section2": post_sentence}).strip().lower()
        
        if 'yes' in response.split('\n')[-1] or 'yes' in response: # Check the start of the string
            return True
        if 'no' in response.split('\n')[-1] or 'no' in response[:20]:
            return False
            
    return False # Default to 'no' (keep chunks together) if LLM is confused


def semantic_chunking(document, llm, model_name='nomic-ai/nomic-embed-text-v1.5', sensitivity=0.9):
    """
    Chunks a document into semantically coherent sections.

    sensitivity = 1.5 # a good starting point for nomic (higher multiplier = larger chunks / fewer breaks)
    """
    # Tokenize the document into paragraphs
    paragraphs_unfilt = document.split('\n')
    paragraphs = [item for item in paragraphs_unfilt if item] #remove empty
   
    # Load a pre-trained embedding model
    model = SentenceTransformer(model_name, trust_remote_code=True)
    # prefix needed for nomic-embed similarity
    prefixed_section = [f"clustering: {s}" for s in paragraphs]
    sentence_embeddings = model.encode(prefixed_section, normalize_embeddings=True, convert_to_tensor=True)
   
    # Calculate cosine similarity between consecutive paragraphs
    cosine_similarities = []
    for i in range(len(paragraphs) - 1):
        cosine_similarities.append(util.cos_sim(sentence_embeddings[i], sentence_embeddings[i+1]))
   
    # Identify chunk boundaries where similarity drops below the threshold
    chunks = []
    sims = [s.item() for s in cosine_similarities]
    mean_sim = np.mean(sims)
    std_sim = np.std(sims)
    dynamic_threshold = mean_sim - (sensitivity * std_sim)

    current_chunk = [paragraphs[0]]
    for i in range(len(paragraphs) - 1):
        # get length of current chunk in characters
        current_len = len("\n".join(current_chunk))
        if current_len > MAX_CHUNK_CHARS:
                chunks.append("\n".join(current_chunk))
                current_chunk = [paragraphs[i+1]]
        elif current_len > MIN_CHUNK_CHARS:
            if cosine_similarities[i].item() < dynamic_threshold:
                if llm_check_semantic_break("\n".join(current_chunk), paragraphs[i+1], llm):
                    # End the current chunk and start a new one
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [paragraphs[i+1]]
            else:
                current_chunk.append(paragraphs[i+1])
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
        except ValueError:
            print(f"Could not find relevance score for chunk: {chunk} got response {response}")




def neo4j_nodes_and_relations(graph, chunks, metadata):
    docs = []
    seq = 0
    for chunk in chunks:
        source = metadata["source"]
        title = metadata["title"]
        unique_id = f"{source}_{title}_chunk_{seq}"
        metadata["chunk_order"] = seq
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

    # Create the base document node
    nquery = """
    CREATE (n:Document {title: $title, author: $author, source: $source})
    RETURN n
    """
    graph.query(nquery, params={"title":metadata["title"],
                                "author":metadata["author"],
                                "source": metadata["source"]})
    
    nquery = """
    MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source}), (b:Chunk {chunk_order: $next, title: $title, source: $source})
    CREATE (a)-[:NEXT_CHUNK]->(b)
    RETURN a, b
    """
    dquery = """
    MATCH (a:Chunk {chunk_order: $seq, title: $title, source: $source}), (b:Document {source: $source, title: $title})
    CREATE (a)-[:FROM_DOCUMENT]->(b)
    RETURN a, b
    """

    # Extract keywords or entities from each chunk and connect nodes
    for i in range(len(chunks)):
        graph.query(dquery, params={"seq":i, "title":metadata["title"], "source":metadata["source"]})
        if i < len(chunks) - 1:
            graph.query(nquery, params={"seq":i, "title":metadata["title"], "source":metadata["source"], "next":i+1})
        keywords = extract_keywords(chunks[i])
        for keyword in keywords:
            # Create a central 'Keyword' node if it doesn't exist
            keyword_node = graph.query(f"MATCH (k:Keyword {{name: '{keyword}'}}) RETURN k", params={"keyword": keyword})
            if not keyword_node:
                graph.query(f"CREATE (k:Keyword {{name: '{keyword}'}})", params={"keyword": keyword})

            # Create a relationship between the chunk and the 'Keyword' node
            graph.query(f"MATCH (c:Chunk {{unique_id: '{unique_id}'}}), (k:Keyword {{name: '{keyword}'}}) MERGE (c)-[:MENTIONS]->(k)", params={"unique_id": unique_id, "keyword": keyword})

    return neo4j_vector


def extract_keywords(text):
    # Return empty set for now.
    keywords = []
    return list(keywords)


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
