# src/API/study_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlparse
from sqlalchemy import text as sa_text
import json
import logging
import os
import re

from agentic.language_tutor.main import LanguageTutorMesh
from agentic.language_tutor.tools.database_tools import get_language_id
from agentic.language_tutor.tools.linguistic import loader_with_result_handle
from agentic.language_tutor.tools.file_management import _get_unified_references_path, read_markdown_content
from agentic.core.llm_client import LLMClient
from agentic.core.moe_orchestrator import MoEOrchestrator
from agentic.language_tutor.tools.database_manager import engine

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class DynamicQuizEndpoint(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        """Fetches all custom or AI questions saved for a specific work."""
        work_id = request.query_params.get('work_id', '8')
        
        # Connect safely using the direct centralized pool engine mapping
        with engine.connect() as conn:
            query = sa_text("""
                SELECT id, topic, question, options, correct_answer, rationale, verification_status, ai_feedback 
                FROM study_quiz_bank 
                WHERE work_id = :work 
                ORDER BY id DESC
            """)
            result = conn.execute(query, {"work": int(work_id)}).fetchall()
            
            question_list = []
            for row in result:
                question_list.append({
                    "id": row[0], 
                    "topic": row[1], 
                    "question": row[2],
                    "options": json.loads(row[3]) if isinstance(row[3], str) else row[3],
                    "correctAnswer": row[4], 
                    "rationale": row[5],
                    "verificationStatus": row[6], 
                    "aiFeedback": row[7]
                })
        return Response({"status": "success", "data": question_list}, status=status.HTTP_200_OK)

    def post(self, request):
        """Creates a new study question and initiates the AI Cross-Verification pass."""
        data = request.data
        orchestrator = MoEOrchestrator()
        llm_client = LLMClient()
        
        work_id = data.get('work_id', 8)
        topic = data.get('topic', 'Linguistic Matrix Verification')
        question = data.get('question', '')
        options = data.get('options', [])
        correct_answer = data.get('correct_answer', '').strip().upper()
        rationale = data.get('rationale', '')

        # 🤖 THE AI VERIFICATION MATRIX GUARDRAIL
        doc_query = "MATCH (d:Document {id: $wid})-[r:FROM_DOCUMENT*1..2]-(c:Chunk) RETURN c.text LIMIT 3"
        v_res = orchestrator.doc_graph.query(doc_query, {"wid": int(work_id)})
        grounding_context = "\n\n".join([str(row[0]) for row in v_res.result_set]) if v_res.result_set else "Metadata active."

        verification_prompt = f"""You are an Expert Academic Audit Engine. Your job is to verify if a study question answer key is factually correct based strictly on the Grounding Context.

[GROUNDING CONTEXT]
{grounding_context}

[STUDY CHALLENGE TO AUDIT]
Question: {question}
Options: {json.dumps(options)}
Stated Correct Answer: {correct_answer}

Analyze the details step-by-step. Determine if the stated correct answer is accurately supported by the context.
Output a clean JSON block exactly like this:
```json
{{
  "status": "VERIFIED",
  "feedback": "Your complete textual rationale detailing why it passes or fails..."
}}
```
"""
        raw_audit, _ = llm_client.call_local_llm(verification_prompt)
        audit_report = llm_client.parse_json_block(raw_audit)
        
        v_status = audit_report.get("status", "PENDING")
        ai_feedback = audit_report.get("feedback", "Audit complete.")

        # Commit permanently using direct engine context managers
        with engine.begin() as conn:
            insert_sql = sa_text("""
                INSERT INTO study_quiz_bank (work_id, topic, question, options, correct_answer, rationale, verification_status, ai_feedback)
                VALUES (:work, :topic, :q, :opts, :ans, :rat, :v_stat, :fb)
                RETURNING id;
            """)
            new_id = conn.execute(insert_sql, {
                "work": int(work_id), 
                "topic": topic, 
                "q": question, 
                "opts": json.dumps(options),
                "ans": correct_answer, 
                "rat": rationale, 
                "v_stat": v_status, 
                "fb": ai_feedback
            }).scalar()

        return Response({
            "status": "success",
            "id": new_id,
            "verificationStatus": v_status,
            "aiFeedback": ai_feedback
        }, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """Deletes a custom quiz question from the master curriculum bank."""
        question_id = request.query_params.get('id')
        
        with engine.begin() as conn:
            conn.execute(sa_text("DELETE FROM study_quiz_bank WHERE id = :id"), {"id": int(question_id)})
            
        return Response({"status": "success", "message": "Entry purged successfully."}, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class ContentIngestionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request, *args, **kwargs):
        # 1. Capture the conference address and target language from the frontend payload
        raw_url = request.data.get('url', '')
        language = request.data.get('language', 'English').strip().title()
        custom_filename = request.data.get('filename', '').strip()

        if isinstance(raw_url, list) and len(raw_url) > 0:
            target_base_url = str(raw_url[0]).strip()
        else:
            target_base_url = str(raw_url).strip()

        # Clean off escaping noise, brackets, quotes, or trailing punctuation completely
        target_base_url = target_base_url.replace('[', '').replace(']', '')
        target_base_url = target_base_url.replace("'", "").replace('"', "")
        target_base_url = target_base_url.split('?')[0].rstrip(',/ ')

        if not target_base_url.startswith('http'):
            return Response({"error": f"Invalid source address structure resolved: {target_base_url}"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Complete the query mapping layout matching the active study track target profile
        lang_query_map = {
            "English": "eng",
            "Spanish": "spa",
            "French": "fra",
            "German": "deu",
            "Korean": "kor"
        }
        
        lang_parameter_tag = lang_query_map.get(language, 'eng')
        sanitized_target_url = f"{target_base_url}?lang={lang_parameter_tag}"

        # 3. Synchronize database language configuration registry checks
        db_lang_info = get_language_id(language)
        if "No matching language" in db_lang_info:
            fallback_codes = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Korean": "ko"}
            if language in fallback_codes:
                db_lang_info = get_language_id(fallback_codes[language])

        if "No matching language" in db_lang_info:
            return Response({"error": f"Language profile parameters '{language}' not configured in SQL lookup tables."}, status=status.HTTP_400_BAD_REQUEST)

        lang_id_defaults = {"English": 1, "Spanish": 2, "French": 3, "German": 4, "Korean": 5}
        target_lang_id = lang_id_defaults.get(language, 1)

        if custom_filename:
            # Clean off path traversal noise and ensure it ends with the target format extension
            sanitized_name = re.sub(r'[^a-zA-Z0-9_.-]', '', custom_filename.replace(' ', '_'))
            if not sanitized_name.lower().endswith('.md'):
                sanitized_name += '.md'
            dynamic_filename = sanitized_name
        else:
            try:
                parsed_url = urlparse(target_base_url)
                path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                if len(path_segments) >= 3:
                    url_slug = "_".join(path_segments[-3:])
                elif path_segments:
                    url_slug = "_".join(path_segments)
                else:
                    url_slug = "downloaded_discourse"
                url_slug = re.sub(r'[^a-zA-Z0-9_-]', '', url_slug)
                dynamic_filename = f"{url_slug}.md"
            except Exception:
                dynamic_filename = "fallback_conference_study.md"

        dynamic_category_path = f"stories/{language.lower()}"

        try:
            # 4. Fetch web text elements using process_and_save_document natively
            from agentic.language_tutor.tools.scraping import get_raw_html, process_and_save_document
            
            logger.info(f"Dispatching dynamic web asset target down the processing channels: {sanitized_target_url}")
            html_content = get_raw_html(sanitized_target_url)
            
            # Persists the talk under a completely unique name and folder structure
            processed = process_and_save_document(html_content, dynamic_filename, dynamic_category_path)
            
            document_raw_text = processed["clean_text"]
            resolved_path = processed["file_path"]

            # Use a clean human-readable title derived from the slug for database display
            display_title = dynamic_filename.replace('_', ' ').replace('.md', '').title()

            # 5. Allocate database registries and split text chunks cleanly into sentences
            work_id = loader_with_result_handle(
                document_text=document_raw_text,
                lang_id=target_lang_id,
                title=display_title,
                path=resolved_path
            )

            # 6. Delegate the auto-quiz question generation directly down your MoEOrchestrator mapping methods
            orchestrator = MoEOrchestrator()
            loaded_suggestions_count = orchestrator.generate_and_cache_suggested_quiz(work_id)

            return Response({
                "status": "success",
                "message": f"Successfully completed dynamic text extraction matching study track: {language}",
                "work_id": work_id,
                "title": display_title,
                "ai_suggestions_loaded": loaded_suggestions_count,
                "processed_url": sanitized_target_url,
                "saved_path": resolved_path
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Mesh execution engine process exception: {str(e)}", exc_info=True)
            return Response({"error": f"Internal pipeline framework exception: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@method_decorator(csrf_exempt, name='dispatch')
class FetchStudyDocumentView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        """
        Dynamically references the registered database path for a given work_id,
        eliminating hardcoded filesystem string assumptions.
        """
        work_id = request.query_params.get('work_id')
        if not work_id:
            return Response({"error": "Missing critical query parameter: work_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Query your database registry to find the dynamic path saved during ingestion
            with engine.connect() as conn:
                query = sa_text("SELECT title, local_path FROM literary_works WHERE id = :work")
                result = conn.execute(query, {"work": int(work_id)}).fetchone()

            if not result:
                return Response({"error": f"No active discourse library match found for Work ID: {work_id}"}, status=status.HTTP_404_NOT_FOUND)

            resolved_title, registered_disk_path = result[0], result[1]

            # 2. Safety Check: If path is unbound, generate a default contextual lookup parameter
            if not registered_disk_path:
                from agentic.language_tutor.tools.file_management import _get_unified_references_path
                base_refs = _get_unified_references_path()
                registered_disk_path = os.path.join(base_refs, "stories", "english", "english_conference_study.md")

            # 3. Verify real-time presence on disk matching your dynamic workspace slugs
            if not os.path.exists(registered_disk_path):
                logger.error(f"Target document missing from storage matrix tracking: {registered_disk_path}")
                return Response({
                    "error": f"Fetch study file requested but missing on disk lookups at: {registered_disk_path}"
                }, status=status.HTTP_404_NOT_FOUND)

            # 4. Extract markdown elements cleanly
            document_content = read_markdown_content(registered_disk_path)

            # 5. Fetch sentences matching your linguistic chunk breakdowns
            with engine.connect() as conn:
                sentence_query = sa_text("SELECT id, full_text FROM sentences WHERE work_id = :work ORDER BY sentence_order ASC")
                sentence_rows = conn.execute(sentence_query, {"work": int(work_id)}).fetchall()

            sentence_payload = []
            for row in sentence_rows:
                sentence_payload.append({
                    "id": row[0],
                    "text": row[1],
                    "isCoreLovePrinciple": False
                })

            return Response({
                "status": "success",
                "title": resolved_title,
                "path": registered_disk_path,
                "content": document_content,
                "data": sentence_payload
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to dynamically fetch study assets: {str(e)}", exc_info=True)
            return Response({"error": f"Internal database retrieval error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    permission_classes = [AllowAny]
    authentication_classes = [] 

    def get(self, request, *args, **kwargs):
        # Gracefully isolate the lowercase language target parameters
        language = request.query_params.get('language', 'English').strip().lower()
        
        try:
            # Leverage your centralized git-root reference helper to map paths accurately
            base_refs = _get_unified_references_path()
            filename = f"{language}_conference_study.md"
            target_path = os.path.normpath(os.path.join(base_refs, "stories", language, filename))
            
            if not os.path.exists(target_path):
                logger.warning(f"Fetch study file requested but missing on disk lookups at: {target_path}")
                return Response({"error": f"No compiled study file found on filesystem at path: {target_path}"}, status=status.HTTP_404_NOT_FOUND)
                
            # Safely extract pristine markdown text lines
            with open(target_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
                
            return Response({"status": "success", "content": markdown_content}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to read target markdown data document: {str(e)}", exc_info=True)
            return Response({"error": f"Internal filesystem read tracking exception: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class CurriculumExplorerListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        """
        Recursively maps the verified curriculum directory layout on disk,
        joining filesystem presence with active tracking database primary keys.
        """
        base_refs = _get_unified_references_path()
        stories_root = os.path.normpath(os.path.join(base_refs, "stories"))
        
        if not os.path.exists(stories_root):
            return Response({"status": "success", "tree": []})

        # Fetch matching DB entries to cross-reference file paths natively
        with engine.connect() as conn:
            db_query = sa_text("SELECT id, title, local_path, language_id FROM literary_works")
            db_records = conn.execute(db_query).fetchall()
            
        path_to_id_map = {row[2]: {"id": row[0], "title": row[1]} for row in db_records if row[2]}

        explorer_tree = []
        lang_id_to_name = {1: "English", 2: "Spanish", 3: "French", 4: "German", 5: "Korean"}

        # Traverse target subfolders dynamically (e.g. references/stories/german/)
        for root, dirs, files in os.walk(stories_root):
            category_name = os.path.basename(root)
            if category_name == "stories":
                continue
                
            category_node = {
                "folder": category_name.upper(),
                "files": []
            }
            
            for f in files:
                if f.endswith('.md'):
                    full_disk_path = os.path.normpath(os.path.join(root, f))
                    db_match = path_to_id_map.get(full_disk_path, {})
                    
                    category_node["files"].append({
                        "filename": f,
                        "work_id": db_match.get("id", None),
                        "displayTitle": db_match.get("title", f.replace('_', ' ').replace('.md', '').title()),
                        "absolutePath": full_disk_path
                    })
            
            if category_node["files"]:
                explorer_tree.append(category_node)

        return Response({"status": "success", "tree": explorer_tree}, status=status.HTTP_200_OK)
