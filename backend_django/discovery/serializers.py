from rest_framework import serializers
from .models import DiscoveryScan, DiscoveredHost

class DiscoveredHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoveredHost
        fields = '__all__'

class DiscoveryScanSerializer(serializers.ModelSerializer):
    discovered_hosts = DiscoveredHostSerializer(many=True, read_only=True)
    
    class Meta:
        model = DiscoveryScan
        fields = '__all__'
        read_only_fields = ('status', 'total_hosts', 'scanned_hosts', 'found_hosts', 'started_at', 'completed_at', 'error_message', 'created_by')
