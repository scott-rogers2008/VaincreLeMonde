# populate_dictionary/parse_target.py

import gzip
import json
import re
from config import POS_MAP
from db import get_db_connection, execute_dictionary_insert, get_language_id
from embeddings import get_ollama_embedding, verify_ollama_status

# UNIVERSAL DEFENSE: Map your DB language keys strictly to Kaikki's standard country ISO codes
KAIKKI_CODES = {
    "Korean": "ko",
    "Spanish": "es",
    "French": "fr",
    "German": "de"
}

# HARDENED TARGET CODES: Matches valid scripts while ignoring foreign leakage
SCRIPT_VALIDATORS = {
    "Korean": re.compile(r'[\uac00-\ud7a3]'),
    "Spanish": re.compile(r'^[^' + r'\u4e00-\u9fff\u3040-\u30ff\u0400-\u04ff' + r']+$'),
    "French": re.compile(r'^[^' + r'\u4e00-\u9fff\u3040-\u30ff\u0400-\u04ff' + r']+$'),
    "German": re.compile(r'^[^' + r'\u4e00-\u9fff\u3040-\u30ff\u0400-\u04ff' + r']+$')
}

def extract_enriched_definition(sense):
    """Extracts glosses, context tags, and cross-references from a sense block."""
    glosses = sense.get("glosses", [])
    if not glosses:
        return None
        
    base_def = " | ".join(glosses) if isinstance(glosses, list) else str(glosses)
    
    clean_base = base_def.strip().rstrip('.')
    raw_words = clean_base.split()
    if len(raw_words) < 2:
        return None

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
    
    # Quality Filter: Ensure we capture rich descriptions, filtering out single words
    words = enriched_def.split()
    if len(words) < 3:
        return None
        
    return enriched_def

def is_word_valid_for_language(word_name: str, language: str) -> bool:
    """Strictly enforces language-specific script boundaries to prevent data cross-contamination."""
    if not word_name:
        return False
    validator = SCRIPT_VALIDATORS.get(language)
    if not validator:
        return True
    if language == "Korean":
        return bool(validator.search(word_name))
    else:
        return bool(validator.match(word_name))

def process_target_language(filepath, language):
    if not verify_ollama_status():
        print("❌ Ollama node is offline. Aborting ingestion loop.")
        return
        
    if language not in KAIKKI_CODES:
        print(f"❌ Unknown language: {language}")
        return

    print(f"🚀 Ingesting {language} entries and native embeddings from: {filepath}...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    dictionary_batch = []
    batch_size = 100
    processed_count = 0
    skipped_count = 0
    low_quality_count = 0
    script_rejected_count = 0
    foreign_leakage_count = 0
    outdated_archaich_count = 0
    regional_count = 0
    raw_word_count = 0

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
                
            raw_word_count += 1
            if raw_word_count % 1000 == 0:
                print(f" -> Processed {raw_word_count} raw lines for {language}...")
            data = json.loads(line)
            
            # STEP 1: BULK FILTER VIA ISO CODES (Bypasses any script string translations)
            line_lang_code = data.get("lang_code", "").strip().lower()
            if line_lang_code != KAIKKI_CODES[language]:
                foreign_leakage_count += 1
                continue

            word_name = data.get("word", "").strip()
            pos_raw = data.get("pos")
            pos_id = POS_MAP.get(pos_raw, 14)
            
            # STEP 2: SCRIPT BOUNDARY ENFORCEMENT
            if not is_word_valid_for_language(word_name, language):
                script_rejected_count += 1
                continue

            senses = data.get("senses", [])
            for sense_idx, sense in enumerate(senses):
                tags = sense.get("tags",[])
                unwanted_tags = {
                    "outdated", "archaic", "obsolete", "historical",
                    "inflection", "form-of", "conjugation", "variant"
                }
                regional_tags = {
                    "cuba", "cuban", "argentina", "argentine", "mexico", "mexican", "colombia", "colombian",
                    "chile", "chilean", "peru", "peruvian", "venezuela", "venezuelan", "bolivia", "ecuador",
                    "andalusia", "andalusian", "canary-islands", "caribbean", "central-america", "latin-america",
                    "scotland", "scottish", "ireland", "irish", "australia", "australian", "canada", "canadian",
                    "austria", "austrian", "switzerland", "swiss", "bavaria", "bavarian", "regional", "dialect",
                    "uk", "british", "england", "scotland", "scottish", "ireland", "irish", "wales", "welsh",
                    "australia", "australian", "canada", "canadian", "new-zealand", "kiwi", "south-africa",
                    "us", "american", "southern-us", "african-american-vernacular-english", "aave", "cockney",
                    "quebec", "quebecois", "canada-french", "belgium", "belgian", 
                    "switzerland-french", "swiss-french", "africa", "african", 
                    "reunion", "louisiana", "cajun", "antilles", "caribbean-french",
                    "switzerland-german", "swiss-german", "austro-bavarian", "low-german",
                    "north-korea", "north-korean", "jeju", "dialectal",
                    "america", "american", "latin-america", "latin-american",
                    "central-america", "central-american", "south-america", "south-american",
                    "caribbean", "caribe", "antilles",
                    "scania", "scanian", "andalusia", "andalusian", "gascony", "gascon",
                    "american-spelling", "british-spelling", "canadian-spelling", 
                    "oxford-spelling", "reformed-spelling", "alternative-spelling",
                    "spain", "españa", "aragon", "aragonese", "aragonés", "castile", "castilian", 
                    "león", "leonese", "extremadura", "extremaduran", "manchego", "murcia",
                    # --- Native Spanish Geographical Spellings ---
                    "sudamérica", "sudamerica", "hispanoamérica", "hispanoamerica", 
                    "iberoamérica", "iberoamerica", "centroamérica", "centroamerica",
                    "norteamérica", "norteamerica",
                    
                    # --- Missing Central/South American Countries & Sub-regions ---
                    "honduras", "honduran", "nicaragua", "nicaraguan", "guatemala", "salvador",
                    "chiloé", "chiloe", "patagonia", "patagonian", "amazon", "amazonian",
                    
                    # --- Peninsular Spanish Dialects (Autonomous Communities) ---
                    "murcia", "murcian", "andalucía", "andalusia", "andaluz", "canarias", 
                    "canarian", "galicia", "galician", "catalonia", "catalan", "aragon", 
                    "aragonese", "valencia", "valencian", "asturias", "asturian",
                    # --- Macro-Regions & Geographic Zones ---
                    "south-cone", "cono-sur", "cono-sur", "central-america", "centro-américa",
                    "centroamerica", "centro-america", "yucatán", "yucatan", "mayab", "peninsular",
                    
                    # --- Peninsular & Sub-National Regions ---
                    "castile", "castilla", "castellano", "honduras", "nicaragua"
                }
                if any(any(unwanted in tag.lower() for unwanted in unwanted_tags) for tag in tags):
                    outdated_archaich_count += 1
                    continue

                if any(any(regional in tag.lower() for regional in regional_tags) for tag in tags):
                    regional_count += 1
                    continue

                definition = extract_enriched_definition(sense)
                if not definition:
                    low_quality_count += 1
                    continue
                    
                if any(f"({regional}" in definition.lower() for regional in regional_tags):
                    regional_count += 1
                    continue

                clean_word = word_name.lower().strip()

                language_id = get_language_id(language)
                
                # RESTART CHECK
                cursor.execute("""
                    SELECT id FROM dictionary_entries 
                    WHERE language_id = %s AND clean_word = %s AND pos_id = %s AND (metadata->>'sense_index')::int = %s;
                """, (language_id, clean_word, pos_id, sense_idx))
                
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                text_to_embed = f"Word: {word_name}. Part of Speech: {pos_raw}. Meaning: {definition}"
                lang_vector = get_ollama_embedding(text_to_embed)
                
                is_mwe = " " in word_name
                metadata_json = json.dumps({"source": "kaikki-wiktionary", "sense_index": sense_idx})
                
                dictionary_batch.append((
                    language_id, pos_id, None, word_name, definition, lang_vector, 
                    None, None, metadata_json, is_mwe, clean_word, 
                ))
                processed_count += 1
                
                if len(dictionary_batch) >= batch_size:
                    execute_dictionary_insert(cursor, dictionary_batch)
                    dictionary_batch = []
                    conn.commit()
                    print(f" -> Stored {processed_count} rows for {language}...")

        if dictionary_batch:
            execute_dictionary_insert(cursor, dictionary_batch)
            conn.commit()
            
    cursor.close()
    conn.close()
    
    print(f"🎉 Completed {language} Ingestion!")
    print(f" - Added rows: {processed_count}")
    print(f" - Skipped (Duplicates): {skipped_count}")
    print(f" - Blocked (Foreign Language Leakage): {foreign_leakage_count}")
    print(f" - Rejected (outdated|archaic|obsolete|historical...): {outdated_archaich_count}")
    print(f" - Rejected (regional specific): {regional_count}")
    print(f" - Rejected (Script boundaries): {script_rejected_count}")
    print(f" - Rejected (Low-quality definitions): {low_quality_count}\n")

if __name__ == "__main__":
    process_target_language("ko-extract.jsonl.gz", "Korean")
    process_target_language("es-extract.jsonl.gz", "Spanish")
    process_target_language("fr-extract.jsonl.gz", "French")
    process_target_language("de-extract.jsonl.gz", "German")
