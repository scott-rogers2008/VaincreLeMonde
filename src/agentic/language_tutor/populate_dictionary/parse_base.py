# populate_dictionary/parse_base.py
import gzip
import json
from config import POS_MAP
from db import get_db_connection, execute_dictionary_insert
from embeddings import get_ollama_embedding, verify_ollama_status

LANG_MAP = {
    "ENG-ZZ-M":"English",
    "KOR-ZZ-M":"Korean",
    "DEU-ZZ-M":"German",
    "FRA-ZZ-M":"French",
    "SPA-ZZ-M":"spanish"}


def extract_enriched_definition(sense):
    """
    Extracts glosses, context tags, and cross-references from a Wiktionary 
    sense block to construct a high-quality definition string.
    Returns None if the definition text fails quality checks.
    """
    glosses = sense.get("glosses", [])
    if not glosses:
        return None

    # Handle structural string vs list edge-cases safely
    base_def = " | ".join(glosses) if isinstance(glosses, list) else str(glosses)
    
    # 1. Capture Domain & Context Tags (e.g., ['archaic', 'chemistry', 'slang'])
    tags = sense.get("tags", [])
    tag_prefix = f"({', '.join(tags)}) " if tags else ""

    # 2. Extract Deep Cross-References (e.g., abbreviations, plurals, alternative forms)
    # Wiktionary uses 'form_of' and 'alt_of' objects to indicate relationships
    cross_references = []
    for ref_type in ["form_of", "alt_of"]:
        ref_list = sense.get(ref_type, [])
        for ref in ref_list:
            if isinstance(ref, dict) and "word" in ref:
                cross_references.append(f"{ref_type.replace('_', ' ')} '{ref['word']}'")
    
    ref_suffix = f" [Cross-reference: {', '.join(cross_references)}]" if cross_references else ""

    # Synthesize the complete enriched definition block
    enriched_def = f"{tag_prefix}{base_def}{ref_suffix}".strip()

    # 3. Quality Guardrail: Reject if the core semantic payload is too short
    if len(enriched_def) < 6:
        return None

    return enriched_def

def process_base_language(filepath, language_id="ENG-ZZ-M"):
    if not verify_ollama_status():
        return
        
    print(f"🚀 Ingesting {LANG_MAP[language_id]} words and native embeddings from: {filepath}...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    dictionary_batch = []
    batch_size = 100
    processed_count = 0
    skipped_count = 0
    low_quality_count = 0

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            word_name = data.get("word")
            pos_raw = data.get("pos")
            pos_id = POS_MAP.get(pos_raw, 14)
            
            if not word_name or not word_name.replace(' ', '').isalpha():
                continue
                
            senses = data.get("senses", [])
            for sense_idx, sense in enumerate(senses):
                glosses = sense.get("glosses", [])
                if not glosses: continue
                
                definition = extract_enriched_definition(sense)
                if not definition:
                    low_quality_count += 1
                    continue

                clean_word = word_name.lower().strip()
                
                # RESTART CHECK: See if we already processed this exact word-sense pair
                cursor.execute("""
                    SELECT id FROM dictionary_entries 
                    WHERE language_id = %s AND clean_word = %s AND pos_id = %s 
                      AND (metadata->>'sense_index')::int = %s;
                """, (language_id, clean_word, pos_id, sense_idx))
                
                if cursor.fetchone():
                    skipped_count += 1
                    continue

                # Generate a purely native language embedding vector from imported text
                text_to_embed = f"Word: {word_name}. Part of Speech: {pos_raw}. Meaning: {definition}"
                lang_vector = get_ollama_embedding(text_to_embed)

                is_mwe = " " in word_name
                metadata_json = json.dumps({"source": "kaikki-wiktionary", "sense_index": sense_idx})
                
                # concept_id is explicitly set to None (NULL) for the clustering phase later
                dictionary_batch.append((
                    language_id, pos_id, None, word_name, definition, lang_vector,
                    None, None, metadata_json, None, is_mwe, clean_word, None
                ))
                processed_count += 1
                
                if len(dictionary_batch) >= batch_size:
                    execute_dictionary_insert(cursor, dictionary_batch)
                    dictionary_batch = []
                    conn.commit()
                    print(f"Stored {processed_count} {LANG_MAP[language_id]} rows... (Skipped {skipped_count} duplicates)")

    if dictionary_batch:
        execute_dictionary_insert(cursor, dictionary_batch)
        conn.commit()
        
    cursor.close()
    conn.close()
    print(f"🎉 {LANG_MAP[language_id]} ingestion finished! Added {processed_count} rows, skipped {skipped_count}.")

if __name__ == "__main__":
    process_base_language("kaikki.org-dictionary-English.jsonl.gz")
    process_base_language("ko-extract.jsonl.gz", "KOR-ZZ-M")
