
from API.views import BlogPostViewSet
from django.urls import path, include
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'posts', BlogPostViewSet)


urlpatterns = [
    path('api/v1/', include(router.urls)),
]
