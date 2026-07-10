# populate_dictionary/remediate_definitions.py
import sys
from db import get_db_connection

def apply_remediation_rule(rule_name, criteria_sql, processing_callback=None):
    """
    An isolated engine to clean database definitions in-place.
    Uses ID-chunking to prevent Postgres named cursor invalidation errors.
    """
    print(f"🔧 Running Remediation Rule: [{rule_name}]...")
    conn = get_db_connection()
    
    # Track metrics
    modified_count = 0
    skipped_count = 0
    
    try:
        # Step 1: Extract all target Primary Key IDs first to isolate the read state
        # (This avoids holding an open server-side cursor during mutations)
        id_cursor = conn.cursor()
        
        # Modify the query context to select the minimum fields needed
        if "select id" not in criteria_sql.lower():
            print("❌ Error: Criteria SQL must select the ID column first.")
            return

        id_cursor.execute(criteria_sql)
        all_rows = id_cursor.fetchall()
        id_cursor.close()
        
        if not all_rows:
            print(f"✅ Rule [{rule_name}] finished. No matching rows found.\n")
            conn.close()
            return
            
        print(f"Found {len(all_rows)} target entries. Processing updates...")
        
        # Step 2: Use a clean cursor loop to execute chunked modifications
        update_cursor = conn.cursor()
        
        # Process entries in chunks of 500
        chunk_size = 500
        for i in range(0, len(all_rows), chunk_size):
            chunk = all_rows[i:i + chunk_size]
            
            for row in chunk:
                row_id = row[0]
                current_text = row[1] if len(row) > 1 else None
                
                # If no callback is provided, we flag the entry to be skipped by the vectorizer
                if processing_callback is None:
                    update_cursor.execute("""
                        UPDATE dictionary_entries 
                        SET remediation_status = 'SKIP_VECTOR',
                            definition_embedding = NULL,
                            original_definition_text = COALESCE(original_definition_text, definition_monolingual),
                            definition_monolingual = '[INVALID_ENTRY]'
                        WHERE id = %s;
                    """, (row_id,))
                else:
                    new_text = processing_callback(current_text, row)
                    
                    if new_text is None or new_text == current_text:
                        skipped_count += 1
                        continue
                        
                    update_cursor.execute("""
                        UPDATE dictionary_entries 
                        SET definition_monolingual = %s,
                            definition_embedding = NULL,
                            remediation_status = 'REQUIRES_REVECTOR',
                            original_definition_text = COALESCE(original_definition_text, %s)
                        WHERE id = %s;
                    """, (new_text, current_text, row_id))
                    
                modified_count += 1
                
            # Safely commit each isolated batch block
            conn.commit()
            print(f"Processed batch... Cumulative modified: {modified_count}")
            
        update_cursor.close()
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error executing rule {rule_name}: {e}")
    finally:
        conn.close()
        
    print(f"✅ Rule [{rule_name}] finished. Modified: {modified_count}, Skipped/No-op: {skipped_count}\n")


# =====================================================================
# DEFINITION CLEANING RULES
# =====================================================================

def run_historical_cleanup():
    """
    Addresses your current database rows: clears out elements under 6 characters.
    """
    # Select both ID and text safely to prevent column offset mismatches
    junk_criteria = """
        SELECT id, definition_monolingual FROM dictionary_entries 
        WHERE LENGTH(TRIM(definition_monolingual)) < 6 
           OR definition_monolingual SIMILAR TO '[A-Za-z]+\.';
    """
    apply_remediation_rule("Flag Low-Length Structural Junk", junk_criteria, processing_callback=None)


if __name__ == "__main__":
    print("🚀 Starting Global Data Remediation Pipeline...")
    run_historical_cleanup()
