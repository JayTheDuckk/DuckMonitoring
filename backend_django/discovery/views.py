from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DiscoveryScan, DiscoveredHost
from .serializers import DiscoveryScanSerializer, DiscoveredHostSerializer
from .tasks import scan_network_task
from inventory.models import Host, apply_host_identity

class DiscoveryScanViewSet(viewsets.ModelViewSet):
    queryset = DiscoveryScan.objects.all().order_by('-created_at')
    serializer_class = DiscoveryScanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        scan = serializer.save(created_by=self.request.user)
        # Start the scan task
        scan_network_task.delay(scan.id)

class DiscoveredHostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DiscoveredHost.objects.all()
    serializer_class = DiscoveredHostSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def add_to_inventory(self, request, pk=None):
        discovered_host = self.get_object()
        
        # Check if host already exists
        if Host.objects.filter(ip_address=discovered_host.ip_address).exists():
            return Response({'error': 'Host with this IP already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        extra = discovered_host.open_ports if isinstance(discovered_host.open_ports, dict) else {}
        now = timezone.now()
        host = Host(
            hostname=discovered_host.hostname or extra.get('mdns_name') or discovered_host.ip_address,
            ip_address=discovered_host.ip_address,
            mac_address=discovered_host.mac_address,
            vendor=discovered_host.manufacturer,
            status='unknown',
        )
        apply_host_identity(host, {
            'ip_address': discovered_host.ip_address,
            'hostname': discovered_host.hostname,
            'mdns_name': extra.get('mdns_name'),
            'apple_model': extra.get('apple_model'),
            'device_class': extra.get('device_class'),
            'confidence': extra.get('confidence'),
            'identification_clues': extra.get('identification_clues') or [],
        }, now=now, created=True)
        host.save()
        
        discovered_host.status = 'added'
        discovered_host.save()
        
        return Response({'status': 'added', 'host_id': host.id})

    @action(detail=True, methods=['post'])
    def ignore(self, request, pk=None):
        discovered_host = self.get_object()
        discovered_host.status = 'ignored'
        discovered_host.save()
        return Response({'status': 'ignored'})
