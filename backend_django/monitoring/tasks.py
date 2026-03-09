from celery import shared_task
from django.utils import timezone
from .models import ServiceCheckConfig, ServiceCheckResult, Check, Metric, UPSMetric, SNMPDeviceMetric
from inventory.models import Host, UPSDevice, SNMPDevice
from core.utils.service_checker import (
    run_service_check, check_ups, check_snmp_device,
    check_ssl_expiry, check_dns, check_http_content
)
import json

@shared_task
def run_all_checks():
    """Batch task to run all checks"""
    # Service Checks
    configs = ServiceCheckConfig.objects.filter(enabled=True)
    for config in configs:
        check_service.delay(config.id)
        
    # UPS Checks
    ups_devices = UPSDevice.objects.filter(enabled=True)
    for ups in ups_devices:
        check_ups_task.delay(ups.id)
        
    # SNMP Device Checks
    snmp_devices = SNMPDevice.objects.filter(enabled=True)
    for device in snmp_devices:
        check_snmp_device_task.delay(device.id)

@shared_task
def check_service(config_id):
    try:
        config = ServiceCheckConfig.objects.get(id=config_id)
        
        # Prepare params
        params = {
            'check_type': config.check_type,
            'host': config.host.ip_address or config.host.hostname,
            'hostname': config.host.hostname,
            'timeout': config.timeout,
            'parameters': config.parameters
        }
        
        # Run check
        status, output, response_time = run_service_check(params)
        
        # Update config
        config.status = status
        config.last_output = output
        config.last_check = timezone.now()
        config.save()
        
        # Store result
        result_obj = ServiceCheckResult.objects.create(
            host=config.host,
            service_check=config,
            check_type=config.check_type,
            check_name=config.check_name,
            status=status,
            output=output,
            response_time=response_time
        )
        
        # Evaluate Alerts
        try:
            from alerts.services import AlertService
            AlertService.evaluate_alerts(config.host, result_obj)
        except Exception as e:
            print(f"Alert evaluation failed: {e}")
        
        # Update Check model for summary
        Check.objects.update_or_create(
            host=config.host,
            check_type=config.check_type,
            check_name=config.check_name,
            defaults={
                'status': status,
                'output': output,
                'last_check': timezone.now()
            }
        )
        
        # Update host status based on service check results
        host = config.host
        host.update_status()
        
    except ServiceCheckConfig.DoesNotExist:
        pass

@shared_task
def check_ups_task(device_id):
    try:
        device = UPSDevice.objects.get(id=device_id)
        
        v3_auth = None
        if device.snmp_version == 3:
            v3_auth = {
                'username': device.snmp_username,
                'security_level': device.snmp_security_level,
                'auth_protocol': device.snmp_auth_protocol,
                'auth_key': device.snmp_auth_key,
                'priv_protocol': device.snmp_priv_protocol,
                'priv_key': device.snmp_priv_key
            }

        status, output, response_time, metrics = check_ups(
            host=device.ip_address,
            model_key=device.model_key,
            community=device.snmp_community,
            snmp_version=device.snmp_version,
            port=device.snmp_port,
            timeout=device.timeout,
            v3_auth=v3_auth
        )
        
        device.status = status
        device.last_check = timezone.now()
        device.save()
        
        # Store metrics
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                UPSMetric.objects.create(
                    ups_device=device,
                    metric_name=k,
                    metric_type='ups',
                    value=v,
                    unit='' # Populate correctly in real impl
                )
                
    except UPSDevice.DoesNotExist:
        pass

@shared_task
def check_snmp_device_task(device_id):
    try:
        device = SNMPDevice.objects.get(id=device_id)
        
        v3_auth = None
        if device.snmp_version == 3:
            v3_auth = {
                'username': device.snmp_username,
                'security_level': device.snmp_security_level,
                'auth_protocol': device.snmp_auth_protocol,
                'auth_key': device.snmp_auth_key,
                'priv_protocol': device.snmp_priv_protocol,
                'priv_key': device.snmp_priv_key
            }

        status, output, response_time, metrics = check_snmp_device(
            host=device.ip_address,
            model_key=device.model_key,
            community=device.snmp_community,
            snmp_version=device.snmp_version,
            port=device.snmp_port,
            timeout=device.timeout,
            v3_auth=v3_auth
        )
        
        device.status = status
        device.last_check = timezone.now()
        device.last_output = output
        device.save()
        
        # Store metrics
        for k, v in metrics.items():
             # Logic similar to original jobs.py
             pass
                
    except SNMPDevice.DoesNotExist:
        pass

@shared_task
def cleanup_old_metrics():
    """
    Deletes metrics and check results older than RETENTION_DAYS
    """
    from datetime import timedelta
    from django.conf import settings
    
    retention_days = getattr(settings, 'RETENTION_DAYS', 30)
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    # Delete old ServiceCheckResults
    deleted_results, _ = ServiceCheckResult.objects.filter(timestamp__lt=cutoff_date).delete()
    
    # Delete old Metrics
    deleted_metrics, _ = Metric.objects.filter(timestamp__lt=cutoff_date).delete()
    
    # Delete old UPSMetrics
    deleted_ups, _ = UPSMetric.objects.filter(timestamp__lt=cutoff_date).delete()
    
    # Delete old SNMPDeviceMetrics
    deleted_snmp, _ = SNMPDeviceMetric.objects.filter(timestamp__lt=cutoff_date).delete()
    
    return f"Cleaned up: {deleted_results} results, {deleted_metrics} metrics, {deleted_ups} UPS metrics, {deleted_snmp} SNMP metrics"
