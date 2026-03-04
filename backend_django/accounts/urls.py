from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, UserProfileView, UserViewSet, AuditLogViewSet, SetupStatusView

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('setup-status/', SetupStatusView.as_view(), name='setup-status'),
    path('me/', UserProfileView.as_view(), name='profile'),
    path('', include(router.urls)),
]
