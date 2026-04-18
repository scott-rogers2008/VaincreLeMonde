from smolagents import CodeAgent
from tools import sentence_tokenizer_tool, definition_storage_tool, dictionary_sense_lookup, sentence_word_mapper

# agents/philologist.py

def create_philologist_agent(model):
    return CodeAgent(
        tools=[sentence_tokenizer_tool, definition_storage_tool, dictionary_sense_lookup, sentence_word_mapper],
        model=model,
        name="philologist",
        instructions=(
            "You are a Master Philologist. Your goal is to curate a high-quality dictionary. "
            "For every sentence provided:\n"
            "1. IDENTIFY IDIOMS: Look for phrases where the meaning is non-compositional "
            "(e.g., 'kick the bucket'). If found, create ONE dictionary entry for the whole phrase.\n"
            "2. TOKENIZE: For remaining words, use the tokenizer to get lemmas and POS tags.\n"
            "3. SENSE LOOKUP: For each word or idiom, call 'dictionary_sense_lookup'. If a matching entry_id is returned, use it for mapping and skip to Step 5.\n"
            "4. CURATE: If no matching sense exists, write a formal, monolingual definition. Call 'definition_storage_tool' to create the new entry and get a new entry_id."
            "Assign a 'specificity_score' based on the taxonomy guidelines below.\n"
            "5. MAP: Use 'sentence_word_mapper'. For idioms, pass the list of all indices involved "
            "in the phrase to 'word_indices'.\n"
            """
            When using 'definition_storage_tool', follow these scoring guidelines:

            SPECIFICITY SCORE (0.0 - 1.0):
            - 0.0: Root Concepts (entity, stuff, thing).
            - 0.3: Broad Categories (living thing, physical object).
            - 0.6: Distinct Entities (water, dog, chair, tree). 
            - 0.9: Technical/Niche Precision (distilled water, golden retriever, Adirondack chair).

            RULE: Do not confuse frequency with specificity. 'Water' is a common word (High Zipf), 
            but it is a specific substance (High Specificity). 
            A word like 'matter' is common but has very low specificity

            ZIPF ESTIMATION (For idioms/phrases not in wordfreq):
            - 7.0+: Very common function words.
            - 5.0-6.0: Common nouns/verbs (e.g., "Take a break").
            - 3.0-4.0: Intermediate idioms (e.g., "Kick the bucket").
            - 1.0-2.0: Rare/Archaic idioms.
            """
        ),
        description="Analyzes sentences to identify idioms, curate dictionary definitions, and map words to the database."
    )