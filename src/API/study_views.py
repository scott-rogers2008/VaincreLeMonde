# src/API/study_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging
import os

from agentic.language_tutor.main import LanguageTutorMesh
from agentic.language_tutor.tools.database_tools import get_language_id
from agentic.language_tutor.tools.file_management import _get_unified_references_path

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ContentIngestionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request, *args, **kwargs):
        # 1. Gracefully capture data values from your frontend payload inputs
        raw_url = request.data.get('url', '')
        language = request.data.get('language', 'English').strip().title()

        # If an array structure leaks through from the template client service, isolate the zero index string
        if isinstance(raw_url, list) and len(raw_url) > 0:
            target_base_url = str(raw_url[0]).strip()
        else:
            target_base_url = str(raw_url).strip()

        # Clean off any escaping noise, trailing brackets, quotes or hanging punctuation marks completely
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
        # Build a pristine, fully-formed address with absolutely no punctuation noise
        sanitized_target_url = f"{target_base_url}?lang={lang_parameter_tag}"

        # 3. Synchronize database registry checks
        db_lang_info = get_language_id(language)
        if "No matching language" in db_lang_info:
            fallback_codes = {"English": "en", "Spanish": "es", "French": "fr", "German": "de", "Korean": "ko"}
            if language in fallback_codes:
                db_lang_info = get_language_id(fallback_codes[language])

        if "No matching language" in db_lang_info:
            return Response({"error": f"Language profile parameters '{language}' not configured in SQL lookup tables."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 4. Dispatch clean parameters directly down the state loop processing stream
            # This generates a perfectly formatted string directive message for your regular expressions to slice
            clean_mesh_directive = f"Process and index the sacred discourse context in {language} from {sanitized_target_url}"
            logger.info(f"Dispatching sanitized web asset configuration target straight to mesh loop: {clean_mesh_directive}")
            
            tutor_mesh = LanguageTutorMesh()
            tutor_mesh.execute_mesh_cycle(clean_mesh_directive)

            return Response({
                "status": "success",
                "message": f"Successfully completed text extraction matching study track: {language}",
                "processed_url": sanitized_target_url
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Mesh execution engine process exception: {str(e)}", exc_info=True)
            return Response({"error": f"Internal pipeline framework exception: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class FetchStudyDocumentView(APIView):
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