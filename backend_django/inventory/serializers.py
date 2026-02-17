from rest_framework import serializers
from .models import Host, HostGroup, UPSDevice, SNMPDevice

class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostGroup
        fields = '__all__'

class HostSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = Host
        fields = '__all__'

class UPSDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UPSDevice
        fields = '__all__'

class SNMPDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SNMPDevice
        fields = '__all__'
