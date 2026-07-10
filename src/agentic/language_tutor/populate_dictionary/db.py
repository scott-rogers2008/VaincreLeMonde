# populate_dictionary/db.py

import psycopg2
from psycopg2.extras import execute_values
from config import DB_CONFIG

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def clear_dictionary_tables():
    print("🧹 Wiping dictionary tables for fresh initialization...")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE dictionary_entries, global_concepts RESTART IDENTITY CASCADE;")
        conn.commit()

def execute_dictionary_insert(cursor, batch_data):
    query = """
        INSERT INTO dictionary_entries 
        (
            language_id, pos_id, register_id, word, definition_monolingual, 
            definition_embedding, frequency_zipf, specificity_score, metadata, 
            cefr_level, is_multiword_expression, clean_word, concept_id
        ) 
        VALUES %s
        ON CONFLICT DO NOTHING;
    """
    execute_values(cursor, query, batch_data)
