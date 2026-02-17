from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DiscoveryScan, DiscoveredHost
from .serializers import DiscoveryScanSerializer, DiscoveredHostSerializer
from .tasks import scan_network_task
from inventory.models import Host

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
        
        # Create host
        host = Host.objects.create(
            hostname=discovered_host.hostname or discovered_host.ip_address,
            ip_address=discovered_host.ip_address,
            status='unknown' # Initial status until checked
        )
        
        discovered_host.status = 'added'
        discovered_host.save()
        
        return Response({'status': 'added', 'host_id': host.id})

    @action(detail=True, methods=['post'])
    def ignore(self, request, pk=None):
        discovered_host = self.get_object()
        discovered_host.status = 'ignored'
        discovered_host.save()
        return Response({'status': 'ignored'})
