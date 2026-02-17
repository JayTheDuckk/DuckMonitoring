from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CheckViewSet, ServiceCheckConfigViewSet, 
    ServiceCheckResultViewSet, MetricViewSet,
    UPSMetricViewSet, SNMPDeviceMetricViewSet,
    DashboardViewSet, WidgetViewSet
)

router = DefaultRouter()
router.register(r'checks', CheckViewSet)
router.register(r'configs', ServiceCheckConfigViewSet)
router.register(r'results', ServiceCheckResultViewSet)
router.register(r'metrics', MetricViewSet)
router.register(r'ups-metrics', UPSMetricViewSet)
router.register(r'snmp-metrics', SNMPDeviceMetricViewSet)
router.register(r'dashboards', DashboardViewSet)
router.register(r'widgets', WidgetViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
