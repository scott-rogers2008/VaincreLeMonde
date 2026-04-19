from smolagents import CodeAgent, LiteLLMModel, tool
from neo4j import GraphDatabase

# Using your existing CHAT_MODEL config from chunker.py
# CHAT_MODEL = "ollama/glm4-tool:9b"

@tool
def manage_knowledge_graph(
    action_type: str, 
    node_label: str, 
    properties: dict, 
    target_node_name: str = None,
    weight: float = 1.0
) -> str:
    """
    Strict tool for Neo4j manipulation.
    Args:
        action_type: 'UPSERT_POSTULATE' or 'LINK_NARRATIVE'
        node_label: 'Postulate', 'Axiom', or 'Observation'
        properties: Dictionary of properties (e.g., {'name': 'Love', 'text': '...'})
        target_node_name: For linking, the name of the existing node to connect to.
        weight: Bayesian confidence score for the relationship.
    """
    # Hardcoded Cypher paths to ensure structural integrity
    if action_type == 'UPSERT_POSTULATE':
        query = "MERGE (n:Postulate {name: $props.name}) SET n += $props RETURN n"
    elif action_type == 'LINK_NARRATIVE':
        query = """
        MATCH (p:{$node_label} {name: $target})
        MERGE (o:Observation {id: $props.id})
        SET o += $props
        MERGE (o)-[r:ILLUSTRATES]->(p)
        SET r.confidence = $weight
        RETURN r
        """
    # Implementation using your existing driver would go here
    return f"Action {action_type} completed for {node_label}."


# Define the tool the agent uses to 'Write' its insights back to your Graph
@tool
def update_graph_relationship(source_id: str, target_postulate: str, rel_type: str, weight: float, reasoning: str):
    """
    Creates or updates a weighted relationship in Neo4j.
    Args:
        source_id: The ID of the chunk/story segment.
        target_postulate: The name of the Axiom/Postulate it connects to.
        rel_type: 'ILLUSTRATES', 'CORROBORATES', or 'CHALLENGES'.
        weight: Bayesian confidence score (0.0 to 1.0).
        reasoning: Brief explanation for the link to minimize hallucinations.
    """
    # Cypher logic goes here to MERGE the relationship with these properties
    return f"Linked {source_id} to {target_postulate} with weight {weight}"

model = LiteLLMModel(model_id="ollama/glm4-tool:9b") # Matching your current setup
weaver_agent = CodeAgent(tools=[update_graph_relationship], model=model)

def run_weaving_iteration(target_postulate_name):
    # 1. Get all chunks from Postgres
    # 2. For each chunk, ask the agent:
    prompt = f"""
    Examine this chunk: {chunk_text}
    How does it relate to the Postulate: '{target_postulate_name}'?
    If it provides evidence (even narrative evidence), use the 'update_graph_relationship' tool.
    Be conservative with weights; if the connection is weak, use a low score.
    """
    weaver_agent.run(prompt)


# Reusing your existing model setup
model = LiteLLMModel(
    model_id="ollama/glm4-tool:9b",
    api_base="http://localhost:11434",
    num_ctx=8192
)

weaver_agent = CodeAgent(tools=[manage_knowledge_graph], model=model)

def weave_post_loading(chunks, is_foundational=True):
    for chunk in chunks:
        if is_foundational:
            # Weave the MD files as Postulates/Axioms
            weaver_agent.run(
                f"Identify the core postulate in this text and upsert it to the graph: {chunk}"
            )
        else:
            # Weave the children's story as weighted Observations
            weaver_agent.run(
                f"Link this story segment to an existing Postulate: {chunk}. "
                "Assign a Bayesian confidence weight based on how clearly it fits."
            )