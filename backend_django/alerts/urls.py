from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertViewSet, AlertRuleViewSet, 
    NotificationChannelViewSet, MaintenanceWindowViewSet
)

router = DefaultRouter()
router.register(r'alerts', AlertViewSet)
router.register(r'rules', AlertRuleViewSet)
router.register(r'channels', NotificationChannelViewSet)
router.register(r'maintenance', MaintenanceWindowViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
