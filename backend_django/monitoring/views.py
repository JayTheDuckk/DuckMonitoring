from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Check, ServiceCheckConfig, ServiceCheckResult, Metric, UPSMetric, SNMPDeviceMetric
from .serializers import (
    CheckSerializer, ServiceCheckConfigSerializer, 
    ServiceCheckResultSerializer, MetricSerializer,
    UPSMetricSerializer, SNMPDeviceMetricSerializer
)
from .tasks import check_service
from core.utils.service_checker import run_service_check

class CheckViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Check.objects.all()
    serializer_class = CheckSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('host', 'status')

class ServiceCheckConfigViewSet(viewsets.ModelViewSet):
    queryset = ServiceCheckConfig.objects.all()
    serializer_class = ServiceCheckConfigSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('host', 'enabled', 'status')
    
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        check_config = self.get_object()
        
        # Try to use Celery if available, otherwise run synchronously
        try:
            from celery import current_app
            # Check if broker is available
            broker_url = current_app.conf.broker_url
            if broker_url and 'redis' in broker_url:
                # Try to connect to Redis
                try:
                    import redis
                    # Parse Redis URL
                    if broker_url.startswith('redis://'):
                        r = redis.from_url(broker_url, socket_connect_timeout=1)
                        r.ping()
                        # Redis is available, use Celery
                        check_service.delay(check_config.id)
                        return Response({'status': 'Check queued'}, status=status.HTTP_202_ACCEPTED)
                except (ImportError, AttributeError):
                    # Redis library not installed
                    pass
                except Exception:
                    # Redis not available, run synchronously
                    pass
        except Exception:
            # Celery/Redis not configured, run synchronously
            pass
        
        # Fallback: Run check synchronously
        try:
            # Prepare params
            params = {
                'check_type': check_config.check_type,
                'host': check_config.host.ip_address or check_config.host.hostname,
                'hostname': check_config.host.hostname,
                'timeout': check_config.timeout,
                'parameters': check_config.parameters or {}
            }
            
            # Run check
            status_result, output, response_time = run_service_check(params)
            
            # Update config
            check_config.status = status_result
            check_config.last_output = output
            check_config.last_check = timezone.now()
            check_config.save()
            
            # Store result
            ServiceCheckResult.objects.create(
                host=check_config.host,
                service_check=check_config,
                check_type=check_config.check_type,
                check_name=check_config.check_name,
                status=status_result,
                output=output,
                response_time=response_time
            )
            
            # Update Check model for summary
            Check.objects.update_or_create(
                host=check_config.host,
                check_type=check_config.check_type,
                check_name=check_config.check_name,
                defaults={
                    'status': status_result,
                    'output': output,
                    'last_check': timezone.now()
                }
            )
            
            # Update host status based on service check results
            host = check_config.host
            host.update_status()
            
            return Response({
                'status': 'Check completed',
                'result': {
                    'status': status_result,
                    'output': output,
                    'response_time': response_time
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['delete'], url_path='clear-results')
    def clear_results(self, request, pk=None):
        check_config = self.get_object()
        check_config.results.all().delete()
        return Response({'status': 'Results cleared'}, status=status.HTTP_204_NO_CONTENT)

class ServiceCheckResultViewSet(viewsets.ModelViewSet):
    queryset = ServiceCheckResult.objects.all().order_by('-timestamp')
    serializer_class = ServiceCheckResultSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('host', 'check_type')

class BaseMetricViewSet(viewsets.ModelViewSet):
    """Base ViewSet for Metrics with summary action"""
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Return the latest value for each metric type for a given host/device.
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Simple aggregation: Dictionary of {metric_name: latest_metric_obj}
        # In a real TSDB (Influx/Prometheus) this is a query.
        # In SQL, we iterate. For small scale this is fine.
        # Optimziation: distinct('metric_name') then get latest?
        # Or just fetch recent ones.
        
        # Get query parameters
        host_id = request.query_params.get('host')
        ups_id = request.query_params.get('ups_device')
        snmp_id = request.query_params.get('snmp_device')
        
        if not (host_id or ups_id or snmp_id):
            return Response([])
            
        # Filter again by specific parent if needed (though filterset_fields handles it mostly)
        if host_id: queryset = queryset.filter(host_id=host_id)
        if ups_id: queryset = queryset.filter(ups_device_id=ups_id)
        if snmp_id: queryset = queryset.filter(snmp_device_id=snmp_id)
        
        # Order by timestamp desc
        queryset = queryset.order_by('-timestamp')
        
        # Retrieve distinct metrics manually
        latest_metrics = {}
        for metric in queryset[:500]: # Limit scan
            if metric.metric_name not in latest_metrics:
                latest_metrics[metric.metric_name] = metric
        
        serializer = self.get_serializer(latest_metrics.values(), many=True)
        return Response(serializer.data)

class MetricViewSet(BaseMetricViewSet):
    queryset = Metric.objects.all().order_by('-timestamp')
    serializer_class = MetricSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('host', 'metric_name')

class UPSMetricViewSet(BaseMetricViewSet):
    queryset = UPSMetric.objects.all().order_by('-timestamp')
    serializer_class = UPSMetricSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('ups_device', 'metric_name')

class SNMPDeviceMetricViewSet(BaseMetricViewSet):
    """
    ViewSet for SNMP Device Metrics.
    """
    queryset = SNMPDeviceMetric.objects.all()
    serializer_class = SNMPDeviceMetricSerializer
    filterset_fields = ['snmp_device', 'metric_name', 'metric_type']

from .models import Dashboard, Widget
from .serializers import DashboardSerializer, WidgetSerializer

class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def widgets(self, request, pk=None):
        dashboard = self.get_object()
        serializer = WidgetSerializer(dashboard.widgets.all(), many=True)
        return Response(serializer.data)

class WidgetViewSet(viewsets.ModelViewSet):
    queryset = Widget.objects.all()
    serializer_class = WidgetSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filterset_fields = ('dashboard', 'widget_type')

    @action(detail=True, methods=['get'])
    def data(self, request, pk=None):
        """
        Return data for the widget based on type and config.
        For now, returns dummy/stub data provided by logic.
        """
        widget = self.get_object()
        data = {}
        
        # Stub implementation
        if widget.widget_type == 'host_status':
            # Needs 'host_id' in config
            data = {'hostname': 'stub-host', 'status': 'up', 'ip_address': '192.168.1.1'}
        elif widget.widget_type == 'alert_list':
            data = []
        elif widget.widget_type == 'service_grid':
            data = [] # List of host statuses
        elif widget.widget_type == 'host_group_summary':
            data = {'up': 5, 'down': 0, 'unknown': 1}
            
        return Response(data)
