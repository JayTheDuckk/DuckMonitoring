from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TopologyViewSet

router = DefaultRouter()
router.register(r'topology', TopologyViewSet, basename='topology')

urlpatterns = [
    path('', include(router.urls)),
]
