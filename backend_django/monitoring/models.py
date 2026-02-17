from django.db import models
from inventory.models import Host, UPSDevice, SNMPDevice

class Check(models.Model):
    STATUS_CHOICES = (
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    )
    
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='checks')
    check_type = models.CharField(max_length=50)
    check_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    output = models.TextField(blank=True, null=True)
    last_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ServiceCheckConfig(models.Model):
    STATUS_CHOICES = (
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    )
    
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='service_checks')
    check_type = models.CharField(max_length=50)
    check_name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    interval = models.IntegerField(default=60)
    timeout = models.IntegerField(default=10)
    parameters = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    last_check = models.DateTimeField(null=True, blank=True)
    last_output = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ServiceCheckResult(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='check_results')
    service_check = models.ForeignKey(ServiceCheckConfig, on_delete=models.CASCADE, related_name='results')
    check_type = models.CharField(max_length=50)
    check_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20)
    output = models.TextField(blank=True, null=True)
    response_time = models.FloatField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['service_check', 'timestamp']),
            models.Index(fields=['host', 'check_type', 'check_name', 'timestamp']),
        ]

class Metric(models.Model):
    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='metrics')
    metric_name = models.CharField(max_length=255, db_index=True)
    metric_type = models.CharField(max_length=50)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['host', 'metric_name', 'timestamp']),
        ]

class UPSMetric(models.Model):
    ups_device = models.ForeignKey(UPSDevice, on_delete=models.CASCADE, related_name='metrics')
    metric_name = models.CharField(max_length=255, db_index=True)
    metric_type = models.CharField(max_length=50)
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['ups_device', 'metric_name', 'timestamp']),
        ]

class SNMPDeviceMetric(models.Model):
    snmp_device = models.ForeignKey(SNMPDevice, on_delete=models.CASCADE, related_name='metrics')
    metric_name = models.CharField(max_length=255, db_index=True)
    metric_type = models.CharField(max_length=50)
    value = models.FloatField(null=True)
    value_string = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['snmp_device', 'metric_name', 'timestamp']),
        ]

from django.conf import settings

class Dashboard(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboards')
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Widget(models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets')
    title = models.CharField(max_length=255, blank=True, null=True)
    widget_type = models.CharField(max_length=50)
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=1)
    config = models.JSONField(default=dict, blank=True)
    refresh_interval = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title or self.widget_type} ({self.dashboard.name})"
