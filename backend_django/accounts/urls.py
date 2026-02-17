from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserProfileView, UserViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', UserProfileView.as_view(), name='profile'),
    path('', include(router.urls)),
]
