# src/API/urls.py (Modified URL registration layout)
from django.urls import path, include
from rest_framework import routers
from API.views import BlogPostViewSet
from API.study_views import ContentIngestionView, FetchStudyDocumentView

router = routers.DefaultRouter()
router.register(r'posts', BlogPostViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('study/ingest/', ContentIngestionView.as_view(), name='study-content-ingest'),
    path('study/fetch/', FetchStudyDocumentView.as_view(), name='study-content-fetch'),
]
