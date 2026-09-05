from datetime import timedelta

from django.utils import timezone
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Host, HostGroup, UPSDevice, SNMPDevice, DeviceObservation, LanWatchSettings,
    apply_imported_host_identity, apply_observation_identity,
    observation_as_host, observation_matches_network, upsert_observation,
)
from .watch import import_or_update_host, sync_hosts_from_observations, watch_status
from .serializers import (
    HostSerializer, HostGroupSerializer, 
    UPSDeviceSerializer, SNMPDeviceSerializer
)
from monitoring.models import ServiceCheckResult, Metric, ServiceCheckConfig
from .discovery import apply_lan_identity_to_host, load_lan_identity_cache, perform_discovery

# Import OID definitions
from core.snmp_oids import SNMP_DEVICE_MODELS
from core.ups_oids import UPS_MODELS
# from monitoring.tasks import check_ups_device, check_snmp_device


class HostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Hosts.
    Includes filtering by status and group.
    """
    queryset = Host.objects.all().prefetch_related('service_checks')
    serializer_class = HostSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('status', 'group')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        from .discovery import load_lan_identity_cache

        ips = list(
            self.get_queryset().exclude(ip_address__isnull=True).values_list('ip_address', flat=True)
        )
        context['observations'] = {
            observation.ip_address: observation
            for observation in DeviceObservation.objects.filter(ip_address__in=ips)
        }
        context['lan_cache'] = load_lan_identity_cache()
        return context

    @action(detail=False, methods=['post'], url_path='clear-ungrouped')
    def clear_ungrouped(self, request):
        is_admin = request.user.is_superuser or getattr(request.user, 'role', None) == 'admin' or getattr(request.user, 'is_admin', False)
        if not is_admin:
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        qs = Host.objects.filter(group__isnull=True)
        count = qs.count()
        qs.delete()
        return Response({'deleted': count})

    @action(detail=True, methods=['delete'], url_path='clear-history')
    def clear_history(self, request, pk=None):
        """
        Clear all monitoring history (results and metrics) for this host.
        """
        host = self.get_object()
        ServiceCheckResult.objects.filter(host=host).delete()
        Metric.objects.filter(host=host).delete()
        return Response({'status': 'Host history cleared'}, status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        host = serializer.save()
        # Auto-create Ping check for manually added hosts
        ServiceCheckConfig.objects.create(
            host=host,
            check_type='ping',
            check_name='Ping Check',
            interval=60,
            enabled=True,
            parameters={'count': 3}
        )


    @action(detail=True, methods=['post'])
    def scan_ports(self, request, pk=None):
        """
        Scan the host for common open ports.
        """
        host = self.get_object()
        from core.utils.service_checker import scan_host_ports
        
        # Run scan (synchronous for now as it's fast enough for common ports, 
        # but could be tasked if list grows)
        results = scan_host_ports(host.ip_address)
        
        return Response(results)

class HostGroupViewSet(viewsets.ModelViewSet):
    queryset = HostGroup.objects.all()
    serializer_class = HostGroupSerializer
    permission_classes = (permissions.IsAuthenticated,)

class UPSDeviceViewSet(viewsets.ModelViewSet):
    queryset = UPSDevice.objects.all()
    serializer_class = UPSDeviceSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('status', 'enabled')
    
    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        Return the list of supported UPS models.
        """
        # Convert dictionary to list format expected by frontend if needed, 
        # or just return the dict. Frontend expects a list in some places or dict.
        # UPSDashboard.js expects `response.data` to be an array or dict?
        # looking at code: `setUpsModels(response.data)`. 
        # `upsModels.map` implies it expects an array.
        # But `SNMPDashboard.js` `setSnmpModels(response.data)` and `Object.values(snmpModels)` implies dict or array.
        
        # Let's standardize on returning a list of model objects for UPS.
        # UPS_MODELS is a dict: {'apc': {...}, 'cyberpower': {...}}
        
        models_list = []
        for key, data in UPS_MODELS.items():
            models_list.append({
                'key': key,
                'name': data.get('name', key),
                'manufacturer': data.get('manufacturer', 'Unknown'),
                'description': data.get('description', ''),
            })
        return Response(models_list)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """
        Trigger an immediate check for this UPS device.
        """
        device = self.get_object()
        from monitoring.tasks import check_ups_device
        check_ups_device.delay(device.id)
        return Response({'status': 'Check queued'}, status=status.HTTP_202_ACCEPTED)

class SNMPDeviceViewSet(viewsets.ModelViewSet):
    queryset = SNMPDevice.objects.all()
    serializer_class = SNMPDeviceSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('status', 'enabled')

    @action(detail=False, methods=['get'])
    def models(self, request):
        """
        Return available SNMP device models (templates).
        """
        # SNMP_DEVICE_MODELS structure is { 'category': [ {key, name...}, ... ] }
        # Frontend logic: `Object.values(snmpModels).flat()` implies it handles the categorized dict.
        return Response(SNMP_DEVICE_MODELS)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """
        Trigger an immediate check for this SNMP device.
        """
        device = self.get_object()
        from monitoring.tasks import check_snmp_device
        check_snmp_device.delay(device.id)
        return Response({'status': 'Check queued'}, status=status.HTTP_202_ACCEPTED)

STALE_OBSERVATION_DAYS = 14
HOST_DOWN_CONDITION = {"field": "status", "operator": "equals", "value": "critical"}


def _ensure_host_down_rule(host):
    from alerts.models import AlertRule

    if AlertRule.objects.filter(host=host, condition_type='host_down').exists():
        return False
    AlertRule.objects.create(
        name=f"{host.hostname} down",
        condition_type='host_down',
        condition=HOST_DOWN_CONDITION,
        severity='critical',
        host=host,
    )
    return True


class DiscoveryViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated,)

    def _merge_stale_observations(self, result, network, now, scanned_ips):
        cutoff = now - timedelta(days=STALE_OBSERVATION_DAYS)
        candidates = DeviceObservation.objects.filter(last_seen__gte=cutoff).exclude(
            ip_address__in=scanned_ips
        )
        stale_hosts = []
        for observation in candidates:
            if not observation_matches_network(observation, network):
                continue
            stale_hosts.append(observation_as_host(observation, seen_this_scan=False))
        if stale_hosts:
            result['hosts'] = list(result.get('hosts') or []) + stale_hosts
        return result
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        network = request.data.get('network')
        scan_type = request.data.get('scan_type', 'quick')
        if not network:
            return Response({'error': 'Network range required'}, status=status.HTTP_400_BAD_REQUEST)
        
        scan_ports = (scan_type == 'full')
        result = perform_discovery(network, scan_ports=scan_ports)
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        scanned_ips = set()
        for host in result.get('hosts') or []:
            observation = upsert_observation(host, network, now=now)
            apply_observation_identity(host, observation, seen_this_scan=True)
            if host.get('ip_address'):
                scanned_ips.add(host['ip_address'])

        imported_by_ip = {
            host.ip_address: host
            for host in Host.objects.filter(ip_address__in=scanned_ips)
        }
        identity_cache = load_lan_identity_cache()
        for host in result.get('hosts') or []:
            apply_imported_host_identity(host, imported_by_ip.get(host.get('ip_address')))
            apply_lan_identity_to_host(host, identity_cache)

        self._merge_stale_observations(result, network, now, scanned_ips)
        for host in result.get('hosts') or []:
            apply_lan_identity_to_host(host, identity_cache)
        return Response(result)

    @action(detail=False, methods=['get'])
    def history(self, request):
        network = request.query_params.get('network')
        cutoff = timezone.now() - timedelta(days=STALE_OBSERVATION_DAYS)
        observations = DeviceObservation.objects.filter(last_seen__gte=cutoff).order_by('-last_seen')
        hosts = []
        identity_cache = load_lan_identity_cache()
        for observation in observations:
            if network and not observation_matches_network(observation, network):
                continue
            host = observation_as_host(observation, seen_this_scan=False)
            apply_lan_identity_to_host(host, identity_cache)
            hosts.append(host)
        return Response({'hosts': hosts})

    @action(detail=False, methods=['get'])
    def changes(self, request):
        """
        Week-over-week discovery diff (default 7 days).

        new: first_seen >= since
        gone: first_seen < since (they used to be around), last_seen older than
              max(since, now-24h), and last_seen still within 30 days
        unnamed_mobile: device_class is privacy_device, mobile, or phone and
                        there is no mdns_name
        """
        try:
            days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            days = 7
        days = max(1, min(days, 90))
        network = request.query_params.get('network')
        now = timezone.now()
        since = now - timedelta(days=days)
        gone_cutoff = max(since, now - timedelta(hours=24))
        recent_floor = now - timedelta(days=30)
        unnamed_classes = {'privacy_device', 'mobile', 'phone'}

        new_hosts = []
        gone_hosts = []
        unnamed_mobile = []

        for observation in DeviceObservation.objects.all():
            if network and not observation_matches_network(observation, network):
                continue
            if not observation.first_seen or not observation.last_seen:
                continue

            host = observation_as_host(observation, seen_this_scan=False)
            if observation.first_seen >= since:
                new_hosts.append(host)
            elif (
                observation.last_seen < gone_cutoff
                and observation.last_seen >= recent_floor
            ):
                gone_hosts.append(host)

            device_class = (observation.device_class or host.get('device_class') or '').lower()
            mdns_name = observation.mdns_name or host.get('mdns_name')
            if device_class in unnamed_classes and not mdns_name:
                unnamed_mobile.append(host)

        return Response({
            'since': since.isoformat(),
            'new': new_hosts,
            'gone': gone_hosts,
            'unnamed_mobile': unnamed_mobile,
        })

    @action(detail=False, methods=['post'])
    def import_hosts(self, request):
        from alerts.pack import ensure_default_alert_pack

        ensure_default_alert_pack()
        hosts_data = request.data.get('hosts', [])
        imported_count = 0
        service_checks_created = 0
        alerts_created = 0
        
        # Detect Gateway for topology
        from .discovery import get_default_gateway
        gateway_ip = get_default_gateway()
        
        created_hosts = []
        now = timezone.now()
        
        for host_data in hosts_data:
            host, created, host_alerts, host_services = import_or_update_host(
                dict(host_data),
                now=now,
                add_services=True,
            )
            if host is None:
                continue
            if created:
                imported_count += 1
            alerts_created += host_alerts
            service_checks_created += host_services
            created_hosts.append(host)
            
        # Topology Linking
        if gateway_ip:
            gateway_host = Host.objects.filter(ip_address=gateway_ip).first()
            if gateway_host:
                for host in created_hosts:
                    # Link to gateway if not gateway itself and no parent set
                    if host.id != gateway_host.id and not host.parent:
                         host.parent = gateway_host
                         host.save()

        return Response({
            'status': 'imported',
            'count': imported_count,
            'service_checks_created': service_checks_created,
            'alerts_created': alerts_created,
        })


class LanWatchView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(watch_status())

    def patch(self, request):
        is_admin = (
            request.user.is_superuser
            or getattr(request.user, 'role', None) == 'admin'
            or getattr(request.user, 'is_admin', False)
        )
        if not is_admin:
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)

        settings = LanWatchSettings.load()
        if 'auto_add_hosts' in request.data:
            settings.auto_add_hosts = bool(request.data.get('auto_add_hosts'))
        if 'network' in request.data:
            settings.network = (request.data.get('network') or '').strip()
        settings.save()

        added = sync_hosts_from_observations(
            create_missing=settings.auto_add_hosts,
            network=settings.network or None,
        )
        payload = watch_status()
        payload['added'] = added
        return Response(payload)
