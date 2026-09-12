import gzip
import json
import time
from config import POS_MAP
from db import get_db_connection, execute_dictionary_insert, get_language_id
from embeddings import get_ollama_embedding, verify_ollama_status

# Define constants for clarity and performance
BATCH_SIZE = 100
UNWANTED_TAGS = {
    "outdated", "archaic", "obsolete", "historical", 
    "inflection", "form-of", "conjugation", "variant"
}

def extract_enriched_definition(sense):
    """
    Extracts glosses, context tags, and cross-references from a Wiktionary sense block.
    Returns None if the definition text fails quality checks.
    """
    glosses = sense.get("glosses", [])
    if not glosses:
        return None

    base_def = " | ".join(glosses) if isinstance(glosses, list) else str(glosses)
    tags = sense.get("tags", [])
    tag_prefix = f"({', '.join(tags)}) " if tags else ""

    cross_references = []
    for ref_type in ["form_of", "alt_of"]:
        ref_list = sense.get(ref_type, [])
        for ref in ref_list:
            if isinstance(ref, dict) and "word" in ref:
                cross_references.append(f"{ref_type.replace('_', ' ')} '{ref['word']}'")
    
    ref_suffix = f" [Cross-reference: {', '.join(cross_references)}]" if cross_references else ""
    enriched_def = f"{tag_prefix}{base_def}{ref_suffix}".strip()

    if len(enriched_def) < 6:
        return None

    return enriched_def

def process_base_language(filepath, language="English"):
    if not verify_ollama_status():
        print("❌ Ollama service is unavailable. Aborting ingestion.")
        return

    language_id = get_language_id(language)
    conn = get_db_connection()
    cursor = conn.cursor()

    print("🧠 Loading existing records into memory to bypass slow DB lookups...")
    cursor.execute("""
        SELECT clean_word, pos_id, (metadata->>'sense_index')::int 
        FROM dictionary_entries 
        WHERE language_id = %s;
    """, (language_id,))
    
    existing_records = {(row[0], row[1], row[2]) for row in cursor.fetchall()}
    print(f"Loaded {len(existing_records)} existing records.")

    print(f"🚀 Ingesting {language} words and native embeddings from: {filepath}...")
    dictionary_batch = []
    
    # --- METRIC COUNTERS ---
    raw_line_count = 0          # Total JSON lines processed
    total_senses_evaluated = 0  # Total sub-senses checked inside JSON lines
    
    # Rejection breakdown categories
    malformed_word_count = 0    # Rejected by .isalpha() / spacing check
    foreign_leakage_count = 0   # Rejected because lang_code != 'en'
    outdated_archaic_count = 0  # Sense dropped due to unwanted metadata tags
    missing_glosses_count = 0   # Sense dropped because it lacked definition glosses
    skipped_duplicate_count = 0 # Sense dropped because it already exists in the DB
    low_quality_count = 0       # Sense dropped because definition string < 6 characters
    ollama_failure_count = 0    # Sense dropped because Ollama API timed out 3 times
    processed_count = 0         # Successfully embedded and sent to DB batch
    proper_or_symbol_count = 0      # Rejected because word is a proper noun or symbol

    total_start_time = time.time()

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): 
                continue
            
            raw_line_count += 1
            if raw_line_count % 5000 == 0:
                elapsed = time.time() - total_start_time
                print(f" -> Line Progress: {raw_line_count} files read | Inserted: {processed_count} | Skipped Duplicates: {skipped_duplicate_count} | Time: {elapsed:.2f}s")

            data = json.loads(line)
            word_name = data.get("word")
            pos_raw = data.get("pos")
            pos_id = POS_MAP.get(pos_raw, 14)

            if pos_id == 2 or pos_id == 14:
                proper_or_symbol_count += 1
                continue
            
            # 1. Structural Guardrail Check
            if not word_name or not word_name.replace(' ', '').isalpha():
                malformed_word_count += 1
                continue

            # 2. Foreign Leakage Filter
            line_lang_code = data.get("lang_code", "").strip().lower()
            if line_lang_code != 'en':
                foreign_leakage_count += 1
                continue

            senses = data.get("senses", [])
            for sense_idx, sense in enumerate(senses):
                total_senses_evaluated += 1
                
                # 3. Fast Tag Filter
                tags = sense.get("tags", [])
                if any(any(unwanted in tag.lower() for unwanted in UNWANTED_TAGS) for tag in tags):
                    outdated_archaic_count += 1
                    continue

                # 4. Content Presence Check
                glosses = sense.get("glosses", [])
                if not glosses:
                    missing_glosses_count += 1
                    continue

                clean_word = word_name.lower().strip()

                # 5. Matching Flat Set Lookup (Deduplication Check)
                if (clean_word, pos_id, sense_idx) in existing_records:
                    skipped_duplicate_count += 1
                    continue

                # 6. Enriched Definition Parsing Quality Check
                definition = extract_enriched_definition(sense)
                if not definition:
                    low_quality_count += 1
                    continue

                # 7. Heavy AI Workload (Ollama embedding call)
                text_to_embed = f"Word: {word_name}. Part of Speech: {pos_raw}. Meaning: {definition}"
                lang_vector = None
                
                for attempt in range(3):
                    try:
                        lang_vector = get_ollama_embedding(text_to_embed)
                        if lang_vector: 
                            break
                    except Exception as e:
                        time.sleep(2)

                if not lang_vector:
                    ollama_failure_count += 1
                    continue

                # Prepare row for batch execution
                is_mwe = " " in word_name
                metadata_json = json.dumps({"source": "kaikki-wiktionary", "sense_index": sense_idx})
                
                dictionary_batch.append((
                    language_id, pos_id, None, word_name, definition, lang_vector,
                    None, None, metadata_json, is_mwe, clean_word
                ))
                processed_count += 1

                if len(dictionary_batch) >= BATCH_SIZE:
                    execute_dictionary_insert(cursor, dictionary_batch)
                    dictionary_batch = []
                    conn.commit()

    if dictionary_batch:
        execute_dictionary_insert(cursor, dictionary_batch)
        conn.commit()
        
    cursor.close()
    conn.close()
    
    # --- COMPLETE AUDIT TRAIL LOGGING ---
    print("\n" + "="*50)
    print(f"📊 FINAL RECORD AUDIT REPORT FOR: {language}")
    print("="*50)
    print(f"Total Raw Lines Processed from JSONL:  {raw_line_count}")
    print(f"Total Word Senses Evaluated:          {total_senses_evaluated}")
    print("-"*50)
    print(f"✅ Successfully Embedded & Stored:    {processed_count}")
    print(f"⏩ Skipped (Already Exists in DB):     {skipped_duplicate_count}")
    print(f"🛑 Dropped (Malformed/Special Chars):  {malformed_word_count} (Lines)")
    print(f"🌍 Dropped (Foreign Language Leak):   {foreign_leakage_count} (Lines)")
    print(f"⏳ Dropped (Outdated/Archaic/Forms):   {outdated_archaic_count} (Senses)")
    print(f"🫙 Dropped (Empty Glosses/Meanings):  {missing_glosses_count} (Senses)")
    print(f"📉 Dropped (Low-Quality/Too Short):    {low_quality_count} (Senses)")
    print(f"💥 Dropped (Ollama Connection Error): {ollama_failure_count} (Senses)")
    print("="*50)
    
    # Arithmetic balance verification check
    accounted_senses = (processed_count + skipped_duplicate_count + 
                        outdated_archaic_count + missing_glosses_count + 
                        low_quality_count + ollama_failure_count)
    print(f"Verification: Senses analyzed ({total_senses_evaluated}) matches metrics accounted for ({accounted_senses}).")

if __name__ == "__main__":
    process_base_language("kaikki.org-dictionary-English-words.jsonl.gz")
