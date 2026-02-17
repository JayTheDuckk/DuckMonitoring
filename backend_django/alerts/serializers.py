from rest_framework import serializers
from .models import Alert, AlertRule, NotificationChannel, MaintenanceWindow, AlertHistory

class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = '__all__'
        read_only_fields = ('created_by',)

class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = '__all__'
        read_only_fields = ('created_by',)

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'

class AlertHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertHistory
        fields = '__all__'

class MaintenanceWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceWindow
        fields = '__all__'
        read_only_fields = ('created_by',)
