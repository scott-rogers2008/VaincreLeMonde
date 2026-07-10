# populate_dictionary/config.py

import os

# Database Configuration
PSQL_USER = os.environ.get("PSQL_USER")
PSQL_PASS = os.environ.get("PSQL_PASSWORD")
PSQL_DB = os.environ.get("PSQL_DB", PSQL_USER)

DB_CONFIG = {
    "dbname": PSQL_DB,
    "user": PSQL_USER,
    "password": PSQL_PASS,
    "host": "localhost",
    "port": 5432
}

# Ollama / AI Settings
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "bge-m3"

# Parts of Speech Mapping
# Updated config.py parts-of-speech routing table
POS_MAP = {
    # 1 | NOUN | Noun
    "noun": 1,
    "abbrev": 1,      # Abbreviations are structurally nouns
    "initialism": 1,
    
    # 2 | PROPN | Proper Noun
    "name": 2,        # First names, surnames, place names
    
    # 3 | VERB | Verb
    "verb": 3,
    "phrase": 3,      # Wiktionary idiom phrases usually act as verbs or nouns
    
    # 4 | AUX | Auxiliary
    "aux": 4,         # Helping verbs
    
    # 5 | ADJ | Adjective
    "adj": 5,
    "adj_sat": 5,     # WordNet satellite adjectives category
    
    # 6 | ADV | Adverb
    "adv": 6,
    
    # 7 | PRON | Pronoun
    "pron": 7,
    
    # 8 | DET | Determiner
    "det": 8,
    "article": 8,
    
    # 9 | ADP | Adposition
    "prep": 9,        # Prepositions
    "postp": 9,       # Postpositions
    
    # 10 | CONJ | Conjunction
    "conj": 10,
    
    # 11 | NUM | Numeral
    "num": 11,
    
    # 12 | PART | Particle
    "part": 12,
    
    # 13 | INTJ | Interjection
    "intj": 13,
    
    # 14 | X | Other
    "symbol": 14,
    "character": 14,
    "punct": 14,
    "suffix": 14,
    "prefix": 14,
    "infix": 14,
    "affix": 14,
    "combining_form": 14
}

