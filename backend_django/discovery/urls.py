from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiscoveryScanViewSet, DiscoveredHostViewSet

router = DefaultRouter()
router.register(r'scans', DiscoveryScanViewSet)
router.register(r'discovered-hosts', DiscoveredHostViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
