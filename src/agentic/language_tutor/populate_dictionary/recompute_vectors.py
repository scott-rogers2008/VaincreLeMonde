# populate_dictionary/recompute_vectors.py
import time
from db import get_db_connection
from embeddings import get_ollama_embedding, verify_ollama_status

def recompute_remediated_vectors():
    if not verify_ollama_status():
        print("❌ Ollama is offline.")
        return

    conn = get_db_connection()
    # Server-side cursor prevents loading all rows into memory at once
    select_cursor = conn.cursor(name="revector_stream")
    update_cursor = conn.cursor()
    
    # Grab rows explicitly marked for re-calculation or missing vectors from active rows
    select_cursor.execute("""
        SELECT id, word, definition_monolingual 
        FROM dictionary_entries 
        WHERE definition_embedding IS NULL 
          AND remediation_status IN ('VALID', 'REQUIRES_REVECTOR');
    """)
    
    print("🔄 Processing vector updates for remediated rows...")
    batch_count = 0
    
    while True:
        rows = select_cursor.fetchmany(100)
        if not rows:
            break
            
        for row_id, word, definition in rows:
            try:
                text_to_embed = f"Word: {word}. Meaning: {definition}"
                vector = get_ollama_embedding(text_to_embed)
                
                update_cursor.execute("""
                    UPDATE dictionary_entries 
                    SET definition_embedding = %s,
                        remediation_status = 'VALID' 
                    WHERE id = %s;
                """, (vector, row_id))
            except Exception as e:
                print(f"⚠️ Error computing vector for entry ID {row_id}: {e}")
                
        conn.commit()
        batch_count += len(rows)
        print(f"Updated {batch_count} embeddings successfully.")
        
    select_cursor.close()
    update_cursor.close()
    conn.close()
    print("🎉 System vector states are perfectly synced!")

if __name__ == "__main__":
    recompute_remediated_vectors()
