from rest_framework import viewsets, permissions
from .models import Alert, AlertRule, NotificationChannel, MaintenanceWindow, AlertHistory
from .serializers import (
    AlertSerializer, AlertRuleSerializer, 
    NotificationChannelSerializer, MaintenanceWindowSerializer,
    AlertHistorySerializer
)

class NotificationChannelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Notification Channels (Slack, Email, etc.).
    """
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for defining Alert Rules.
    """
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('host', 'enabled', 'severity')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing active and past Alerts.
    """
    queryset = Alert.objects.all().order_by('-triggered_at')
    serializer_class = AlertSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('status', 'severity', 'host')

class MaintenanceWindowViewSet(viewsets.ModelViewSet):
    """
    ViewSet for scheduling Maintenance Windows to suppress alerts.
    """
    queryset = MaintenanceWindow.objects.all()
    serializer_class = MaintenanceWindowSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
