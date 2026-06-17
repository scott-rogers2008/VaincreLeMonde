# src/agentic/language_tutor/main.py
import os
import json
import re
import urllib.request
from utils import get_git_root

# Pull low-level capability tools directly from your existing modules
from language_tutor.tools.database_tools import get_language_id, db_content_reader
from language_tutor.tools.library_tools import library_search, register_work
from language_tutor.tools.file_management import directory_explorer, read_markdown_content
from language_tutor.tools.scraping import get_raw_html, process_and_save_document
from language_tutor.tools.linguistic import sentence_splitter, loader as db_loader
from language_tutor.tools.history import update_agent_memory, get_shared_memory

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b" # Optimized configuration model for local reasoning

class LanguageTutorMesh:
    def __init__(self):
        print("🎓 Consolidated Language Tutor Mesh Operational (Pure Function Routing Mode)")

    def _call_llm(self, prompt: str) -> str:
        """Low-level execution engine to prevent context crashes on local hardware."""
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192}
        }
        try:
            req = urllib.request.Request(
                OLLAMA_URL, data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode('utf-8'))["response"]
        except Exception as e:
            return f'{{"error": "Ollama interaction failed: {str(e)}"}}'

    def _parse_structured_json(self, raw_text: str) -> dict:
        """Resiliently pulls structured execution parameters out of raw LLM streams."""
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            json_str = json_match.group(1) if json_match else raw_text
            if not json_match:
                bracket_match = re.search(r'(\{.*?\})', raw_text, re.DOTALL)
                json_str = bracket_match.group(1) if bracket_match else raw_text
            return json.loads(json_str.strip().replace("\n", " "))
        except Exception:
            return {"status": "FAIL", "explanation": f"Failed to extract clean JSON payload: {raw_text}"}

    def execute_mesh_cycle(self, user_task: str):
        """
        State Machine Orchestrator. Replaces the multi-agent 'Librarian' loop by 
        guiding the local model sequentially through the required actions.
        """
        print(f"\n🚀 Starting document workflow processing sequence for target task: '{user_task}'")
        
        # ---------------------------------------------------------------------
        # PHASE 1: CODEX PERSONA LAYER (Language Profile Verification)
        # ---------------------------------------------------------------------
        print("  ├── [Executing Codex Persona]: Verifying target language code signature...")
        codex_prompt = f"""
        You are the Codex Specialist. Your task is to look at the user request and isolate the target language name.
        User Request: {user_task}
        Output a clean JSON block specifying the exact name of the target language to look up.
        Shape: ```json {{"target_language": "German"}} ```
        """
        lang_target = self._parse_structured_json(self._call_llm(codex_prompt)).get("target_language", "English")
        db_lang_info = get_language_id(lang_target)
        print(f"  │    └── DB Lookup Outcome: {db_lang_info}")
        
        # Extract the integer ID cleanly using a regex matcher pass
        lang_id_match = re.search(r'Found:\s*(\d+)', db_lang_info)
        if not lang_id_match:
            print("  ❌ Technical Alignment Aborted: Target language code signature missing from DB registries.")
            return
        lang_id = int(lang_id_match.group(1))
        update_agent_memory("codex", "current_lang_id", str(lang_id))

        # ---------------------------------------------------------------------
        # PHASE 2: SCOUT PERSONA LAYER (Document Sourcing & HTML Scraping)
        # ---------------------------------------------------------------------
        print("  ├── [Executing Scout Persona]: Assessing workspace storage trees...")
        url_match = re.search(r'https?://[^\s]+', user_task)
        source_url = url_match.group(0) if url_match else "https://grimmstories.com"
        
        # Check library for pre-existing records to prevent redundant processing loops
        existing_records = library_search(lang_target)
        print(f"  │    └── Internal Library Scan: Checked matches for '{lang_target}' catalog rows.")

        print("  │    └── Sourcing target HTML content stream...")
        try:
            raw_html = get_raw_html(source_url)
            # Create standard relative file descriptors based on the language profile
            filename = f"{lang_target.lower()}_story_import.md"
            category_path = f"stories/{lang_target.lower()}"
            
            # Strip boilerplate structural HTML markers and write clean markdown to disk
            scraping_result = process_and_save_document(raw_html, filename, category_path)
            local_md_path = scraping_result["file_path"]
            clean_document_text = scraping_result["clean_text"]
            print(f"  │    └── Document written safely to storage disk: {local_md_path}")
        except Exception as e:
            print(f"  ❌ Content Sourcing Failure: {e}")
            return

        # ---------------------------------------------------------------------
        # PHASE 3: LIBRARIAN LAYER (Database Registry Entry Verification)
        # ---------------------------------------------------------------------
        print("  ├── [Executing Librarian Persona]: Committing metadata registries to database...")
        title_extraction_prompt = f"""
        Extract a clean, readable short title for this document text.
        Text Snippet: {clean_document_text[:400]}
        Output a clean JSON block: ```json {{"title": "Hansel und Gretel"}} ```
        """
        doc_title = self._parse_structured_json(self._call_llm(title_extraction_prompt)).get("title", "Imported Story Work")
        
        # Save a new parent structural metadata context tracking token
        registration_log = register_work(
            title=doc_title,
            lang_id=lang_id,
            work_type="SHORT_STORY",
            source_url=source_url,
            path=local_md_path,
            author="Extracted Profile Engine"
        )
        print(f"  │    └── Database Context Log: {registration_log}")
        
        work_id_match = re.search(r'ID:\s*(\d+)', registration_log)
        if not work_id_match:
            print("  ❌ Registry Exception: Failed to generate a valid relational tracking key link.")
            return
        work_id = int(work_id_match.group(1))
        update_agent_memory("librarian", "current_work_id", str(work_id))

        # ---------------------------------------------------------------------
        # PHASE 4: PHILOLOGIST LAYER (Linguistic Processing Pass)
        # ---------------------------------------------------------------------
        print("  ├── [Executing Philologist Persona]: Chunking document text and processing vocab elements...")
        # Reads the saved markdown file to verify full file structure
        verified_text = read_markdown_content(local_md_path)
        
        # Use our standard linguistic loader tool to split, verify, and populate the DB.
        # This function loops through paragraphs and processes vocab elements via its internal Philologist rules.
        db_loader(verified_text, lang_id, work_id)
        print("  │    └── Complete structural database load routine finalized successfully.")

        # ---------------------------------------------------------------------
        # PHASE 5: QUALITY CONTROL LAYER (Verification Pass)
        # ---------------------------------------------------------------------
        print("  └── [Executing Quality Control]: Confirming data structure records...")
        saved_sentences = db_content_reader(work_id=work_id)
        sentence_count = len(saved_sentences)
        
        print("\n✨ ================= WORKFLOW COMPLETE ================= ✨")
        print(f"  Successfully processed and loaded story: '{doc_title}'")
        print(f"  Database Reference Keys -> Language ID: {lang_id} | Work ID: {work_id}")
        print(f"  Storage Footprint -> Persistent Table Records: {sentence_count} Sentences Indexed.")
        print("=========================================================== \n")

if __name__ == "__main__":
    tutor_mesh = LanguageTutorMesh()
    
    print("--- Language Tutor Collaborative Session ---")
    user_request = input("\nWhat story and language are we working on today?\n> ").strip()
    if not user_request:
        user_request = "Hansel and Gretel in German from https://grimmstories.com"
        
    tutor_mesh.execute_mesh_cycle(user_request)
