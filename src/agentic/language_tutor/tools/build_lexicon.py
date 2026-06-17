# src/agentic/language_tutor/tools/build_lexicon.py
import os
import json
from datetime import date
from falkordb import FalkorDB

# 1. Import NLTK WordNet access layers
import nltk
from nltk.corpus import wordnet as wn

# Import your local operational tool dependencies
from .embeddings import get_embeddings
from .database_manager import engine
from sqlalchemy import text as sa_text

EMBED_MODEL = "bge-m3"

class HybridLexiconPipeline:
    def __init__(self):
        # Establish low-overhead native connection to your WSL2 FalkorDB container
        self.db = FalkorDB(host='localhost', port=6379)
        self.graph = self.db.select_graph("document_rag_graph")

    def initialize_indexes(self):
        """Provisions native 1024D HNSW vector slots inside FalkorDB."""
        try:
            self.graph.query(
                "CREATE VECTOR INDEX FOR (s:Sense) ON (s.embedding) "
                "OPTIONS {dimension: 1024, similarityFunction: 'cosine'}"
            )
            print("✅ FalkorDB vector-graph lexicon space active.")
        except Exception:
            pass

    def run_ingestion_pass(self, wiktextract_file_path: str, target_lang_id: str, limit_entries: int = 200):
        """
        Processes your hybrid lexicon database pass.
        Streams modern definitions from Wiktextract and injects structural 
        relational edges (Hypernyms, Antonyms) directly from WordNet.
        """
        print(f"🚀 Initializing hybrid ingestion pipeline for language context: {target_lang_id}")
        self.initialize_indexes()
        
        # Verify the target input dataset file exists on disk
        if not os.path.exists(wiktextract_file_path):
            print(f"❌ Aborted: Target Wiktextract source file not found at path: {wiktextract_file_path}")
            print("👉 Please ensure you have downloaded the target .jsonl dictionary dump from kaikki.org")
            return

        lang_prefix = target_lang_id[:2].lower() # e.g., 'de' or 'en'
        success_count = 0

        # --- MEMORY-SAFE REFILL LOOP: STREAMING LINE-BY-LINE ---
        with open(wiktextract_file_path, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    entry_data = json.loads(line.strip())
                    
                    # 1. STRICT ENTRY FILTER: Verify the entry's parent language block matches
                    # Kaikki files use the 'lang_code' attribute to mark the word's true language origin.
                    if entry_data.get("lang_code") != lang_prefix:
                        continue
                        
                    word = entry_data.get("word", "").strip().lower()
                    
                    # 2. ALPHABET GUARDRAIL: Skip entries containing english characters if indexing a non-latin script,
                    # or apply regex guards if you want to skip words containing unexpected character sets.
                    if not word or any(char.isdigit() for char in word):
                        continue

                    pos = entry_data.get("pos", "NOUN").upper()
                    senses = entry_data.get("senses", [])
                    if not senses:
                        continue

                    # --- EXTRACT CLEAN SENSES AND INJECT ---
                    for sense_idx, sense in enumerate(senses):
                        glosses = sense.get("glosses", [])
                        if not glosses:
                            continue
                        definition_text = glosses # Rich english string description of the foreign word

                        print(f" ├── [VERIFIED TARGET]: '{word}' ({pos}) -> Ingesting Sense Cluster...")
                        
                        # Process embeddings and sync down to PostgreSQL + FalkorDB
                        raw_vector = get_embeddings(definition_text)
                        postgres_entry_id = self._save_to_postgresql(word, pos, definition_text, target_lang_id, raw_vector)
                        self._sync_nodes_to_falkor(word, pos, target_lang_id, postgres_entry_id, definition_text, raw_vector)

                    # Weave the WordNet relationship pathways for this verified word
                    self._weave_wordnet_relationships(word, target_lang_id)
                    
                    success_count += 1
                    if success_count >= limit_entries:
                        print(f"🏁 Target limit checkpoint reached ({limit_entries} words).")
                        break

                except Exception:
                    continue

        print(f"✨ Ingestion pass complete! Populated {success_count} hybrid vocabulary paths.")

    def _save_to_postgresql(self, word, pos, definition, lang_id, vector_data) -> int:
        """Internal relational persistence wrapper."""
        vector_str = f"[{','.join(map(str, vector_data))}]"
        with engine.begin() as conn:
            query = sa_text("""
                INSERT INTO dictionary_entries (language_id, pos_id, register_id, word, definition_monolingual, definition_embedding, frequency_zipf, specificity_score)
                VALUES (:lang, (SELECT id FROM parts_of_speech WHERE tag = :pos LIMIT 1), (SELECT id FROM registers WHERE tag = :reg LIMIT 1), :word, :def, :vec, 1.0, 0.5)
                RETURNING id
            """)
            return conn.execute(query, {
                "lang": lang_id, "pos": pos, "reg": "NEUTRAL", "word": word, "def": definition, "vec": vector_str
            }).scalar()

    def _sync_nodes_to_falkor(self, word, pos, lang_id, pg_id, definition, vector_data):
        """Creates parent Lexeme backbone vertices and attaches Wiktextract definitions."""
        # Merge baseline Lexeme entity tracker
        lexeme_query = "MERGE (l:Lexeme {text: $word, language: $lang}) SET l.pos = $pos"
        self.graph.query(lexeme_query, {"word": word, "lang": lang_id, "pos": pos})

        # Secure definition node linked to parent with native vecf32 tracking configurations
        sense_query = """
            MATCH (l:Lexeme {text: $word, language: $lang})
            CREATE (s:Sense {
                postgres_id: $pg_id,
                definition: $def,
                embedding: vecf32($vector),
                last_update: $today
            })
            MERGE (l)-[:HAS_SENSE]->(s)
        """
        self.graph.query(sense_query, {
            "word": word, "lang": lang_id, "pg_id": int(pg_id), "def": definition, "vector": vector_data, "today": date.today().isoformat()
        })

    def _weave_wordnet_relationships(self, word, lang_id):
        """Queries local NLTK C-wrappers to locate antonyms or hypernyms, drawing graph edges."""
        # Query WordNet synsets for the parsed target word string entry
        synsets = wn.synsets(word)
        if not synsets:
            return

        for synset in synsets:
            # 1. Process Hypernyms (broader categorizations, e.g., 'dog' -> 'canine')
            for hypernym in synset.hypernyms():
                for lemma in hypernym.lemmas():
                    related_word = lemma.name().lower().replace("_", " ")
                    if related_word != word:
                        self._create_graph_edge(word, related_word, "HAS_HYPERNYM", lang_id)

            # 2. Process Antonyms (direct opposites, e.g., 'hot' -> 'cold')
            for lemma in synset.lemmas():
                for antonym in lemma.antonyms():
                    related_word = antonym.name().lower().replace("_", " ")
                    self._create_graph_edge(word, related_word, "HAS_ANTONYM", lang_id)

    def _create_graph_edge(self, word_a, word_b, relationship, lang_id):
        """Draws native structural direction vector pathways inside your container."""
        # Ensure destination node paths are registered before allocating edge lines
        merge_query = "MERGE (l:Lexeme {text: $w, language: $lang})"
        self.graph.query(merge_query, {"w": word_a, "lang": lang_id})
        self.graph.query(merge_query, {"w": word_b, "lang": lang_id})

        edge_query = f"""
            MATCH (a:Lexeme {{text: $word_a, language: $lang}})
            MATCH (b:Lexeme {{text: $word_b, language: $lang}})
            MERGE (a)-[:{relationship}]->(b)
        """
        try:
            self.graph.query(edge_query, {"word_a": word_a, "word_b": word_b, "lang": lang_id})
        except Exception:
            pass

if __name__ == "__main__":
    pipeline = HybridLexiconPipeline()
    # Ensure this matches your local extracted JSONL dictionary filename exactly
    pipeline.run_ingestion_pass("de-wiktionary.jsonl", "DEU-ZZ-M", limit_entries=100)