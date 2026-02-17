from django.db import models
from django.conf import settings
from inventory.models import Host, HostGroup
from monitoring.models import ServiceCheckConfig

class NotificationChannel(models.Model):
    CHANNEL_TYPES = (
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('discord', 'Discord'),
        ('webhook', 'Webhook'),
    )
    
    name = models.CharField(max_length=255)
    channel_type = models.CharField(max_length=50, choices=CHANNEL_TYPES)
    config = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AlertRule(models.Model):
    SEVERITY_CHOICES = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True, blank=True)
    host_group = models.ForeignKey(HostGroup, on_delete=models.CASCADE, null=True, blank=True)
    
    condition_type = models.CharField(max_length=50)
    condition = models.JSONField(default=dict)
    
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    duration_seconds = models.IntegerField(default=0)
    
    channels = models.ManyToManyField(NotificationChannel, blank=True)
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Alert(models.Model):
    STATUS_CHOICES = (
        ('firing', 'Firing'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    )
    SEVERITY_CHOICES = (
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    )

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True, blank=True)
    service_check = models.ForeignKey(ServiceCheckConfig, on_delete=models.CASCADE, null=True, blank=True)
    
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, null=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='firing', db_index=True)
    
    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='acknowledged_alerts', on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_note = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='resolved_alerts', on_delete=models.SET_NULL, null=True, blank=True)
    
    last_notification_at = models.DateTimeField(null=True, blank=True)
    notification_count = models.IntegerField(default=0)

class AlertHistory(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=50)
    previous_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    actor_type = models.CharField(max_length=20, default='system')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

class MaintenanceWindow(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    host = models.ForeignKey(Host, on_delete=models.CASCADE, null=True, blank=True)
    host_group = models.ForeignKey(HostGroup, on_delete=models.CASCADE, null=True, blank=True)
    all_hosts = models.BooleanField(default=False)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    suppress_alerts = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
