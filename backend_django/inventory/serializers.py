import re

from rest_framework import serializers
from monitoring.models import ServiceCheckConfig
from .models import Host, HostGroup, UPSDevice, SNMPDevice
from .watch import enrich_host_api_dict

_PING_MS = re.compile(r'([\d.]+)\s*ms', re.IGNORECASE)

class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostGroup
        fields = '__all__'

class ServiceCheckBriefSerializer(serializers.ModelSerializer):
    port = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCheckConfig
        fields = ('id', 'check_type', 'check_name', 'status', 'enabled', 'port', 'last_check', 'last_output')

    def get_port(self, obj):
        return (obj.parameters or {}).get('port')

class HostSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    service_checks = ServiceCheckBriefSerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()
    
    class Meta:
        model = Host
        fields = '__all__'

    def get_services(self, instance):
        if instance.discovered_services:
            return instance.discovered_services
        checks = []
        for check in instance.service_checks.all():
            port = (check.parameters or {}).get('port')
            if port:
                checks.append({
                    'port': port,
                    'service': check.check_type,
                    'state': 'open',
                    'status': check.status,
                })
        return checks

    def to_representation(self, instance):
        data = super().to_representation(instance)
        observations = self.context.get('observations') or {}
        enrich_host_api_dict(
            data,
            observation=observations.get(instance.ip_address),
            lan_cache=self.context.get('lan_cache'),
        )
        if not data.get('services'):
            data['services'] = self.get_services(instance)
        if data.get('latency_ms') in (None, ''):
            for check in instance.service_checks.all():
                if check.check_type != 'ping' or not check.last_output:
                    continue
                match = _PING_MS.search(check.last_output)
                if match:
                    data['latency_ms'] = float(match.group(1))
                    break
        return data

class UPSDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UPSDevice
        fields = '__all__'

class SNMPDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SNMPDevice
        fields = '__all__'
