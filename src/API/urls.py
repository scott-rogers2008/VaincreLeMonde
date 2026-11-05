# src/API/urls.py
from django.urls import path, include
from rest_framework import routers
from API.views import BlogPostViewSet
from API.study_views import (ContentIngestionView, FetchStudyDocumentView,
                             DynamicQuizEndpoint, CurriculumExplorerListView)

router = routers.DefaultRouter()
router.register(r'posts', BlogPostViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('study/ingest/', ContentIngestionView.as_view(), name='study-content-ingest'),
    path('study/fetch/', FetchStudyDocumentView.as_view(), name='study-content-fetch'),
    path('study/fetch/quiz/bank/', DynamicQuizEndpoint.as_view(), name='quiz-bank-handler'),
    path('study/explorer/list/', CurriculumExplorerListView.as_view(), name='curriculum-explorer'),
]
