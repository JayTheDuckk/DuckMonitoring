from rest_framework import serializers
from .models import Check, ServiceCheckConfig, ServiceCheckResult, Metric, UPSMetric, SNMPDeviceMetric

class CheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = '__all__'

class ServiceCheckConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCheckConfig
        fields = '__all__'

class ServiceCheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCheckResult
        fields = '__all__'

class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = '__all__'

class UPSMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = UPSMetric
        fields = '__all__'

class SNMPDeviceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SNMPDeviceMetric
        fields = '__all__'

from .models import Dashboard, Widget

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = '__all__'
        read_only_fields = ('dashboard',)

class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')
