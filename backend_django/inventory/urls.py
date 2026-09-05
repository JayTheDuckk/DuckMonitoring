from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HostViewSet, HostGroupViewSet, 
    UPSDeviceViewSet, SNMPDeviceViewSet, 
    DiscoveryViewSet, LanWatchView,
)

router = DefaultRouter()
router.register(r'hosts', HostViewSet)
router.register(r'groups', HostGroupViewSet)
router.register(r'ups', UPSDeviceViewSet)
router.register(r'snmp', SNMPDeviceViewSet)
router.register(r'discovery', DiscoveryViewSet, basename='discovery')

urlpatterns = [
    path('watch/', LanWatchView.as_view(), name='lan-watch'),
    path('', include(router.urls)),
]
