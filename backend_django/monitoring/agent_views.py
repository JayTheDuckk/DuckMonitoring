from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db import transaction
from inventory.models import Host
from .models import Check, Metric, ServiceCheckResult

class AgentRegisterView(views.APIView):
    permission_classes = [AllowAny] # Ideally secure this with a shared secret or token

    def post(self, request):
        agent_id = request.data.get('agent_id')
        hostname = request.data.get('hostname')
        ip_address = request.data.get('ip_address')

        if not agent_id or not hostname:
            return Response({'error': 'agent_id and hostname are required'}, status=status.HTTP_400_BAD_REQUEST)

        host, created = Host.objects.update_or_create(
            agent_id=agent_id,
            defaults={
                'hostname': hostname,
                'ip_address': ip_address,
                'status': 'up', # Assume up on registration
                'last_check': timezone.now()
            }
        )

        return Response({'status': 'registered', 'host_id': host.id})

class AgentSubmitView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        agent_id = request.data.get('agent_id')
        checks = request.data.get('checks', [])
        metrics = request.data.get('metrics', [])

        if not agent_id:
            return Response({'error': 'agent_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            host = Host.objects.get(agent_id=agent_id)
        except Host.DoesNotExist:
            return Response({'error': 'Host not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # Update Host Status
            host.last_check = timezone.now()
            host.status = 'up' # Active because it's reporting
            host.save()

            # Process Checks
            for check_data in checks:
                check_name = check_data.get('name')
                check_type = check_data.get('type')
                status_val = check_data.get('status')
                output = check_data.get('output')

                # Update or Create Current Check Status
                Check.objects.update_or_create(
                    host=host,
                    check_name=check_name,
                    check_type=check_type,
                    defaults={
                        'status': status_val,
                        'output': output,
                        'last_check': timezone.now()
                    }
                )

                # Store Check Result History
                # We need to link this to a ServiceCheckConfig if possible, but for now we might skip that relation or make it optional
                # The ServiceCheckResult model requires 'service_check' (ForeignKey to ServiceCheckConfig). 
                # If the agent reports checks that aren't configured in ServiceCheckConfig, we can't store them in ServiceCheckResult easily 
                # unless we make the FK optional or auto-create config.
                # For this implementation, let's assume we skip ServiceCheckResult if no config exists, or we modify the model.
                # EDIT: checks are usually configured on server, agent runs them. 
                # But here agent seems to run its own checks?
                # The agent.py (which I saw earlier) runs "built-in" checks (cpu, memory, disk).
                # These might NOT have ServiceCheckConfig.
                # Check model is for "current status".
                # ServiceCheckResult is for "history".
                
                # Let's check if the user requires ServiceCheckResult for these.
                # For now, just updating Check is good for "Status".

            # Process Metrics
            for metric_data in metrics:
                Metric.objects.create(
                    host=host,
                    metric_name=metric_data.get('name'),
                    metric_type=metric_data.get('type'),
                    value=metric_data.get('value'),
                    unit=metric_data.get('unit')
                )

        return Response({'status': 'received'})
