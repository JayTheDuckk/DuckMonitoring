from django.db import models
from django.conf import settings

class DiscoveryScan(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    subnet = models.CharField(max_length=50, help_text="CIDR subnet to scan (e.g., 192.168.1.0/24)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_hosts = models.IntegerField(default=0)
    scanned_hosts = models.IntegerField(default=0)
    found_hosts = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan {self.subnet} ({self.status})"

class DiscoveredHost(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('ignored', 'Ignored'),
        ('added', 'Added'),
    )
    
    scan = models.ForeignKey(DiscoveryScan, on_delete=models.CASCADE, related_name='discovered_hosts')
    ip_address = models.GenericIPAddressField()
    hostname = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    os_guess = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    open_ports = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('scan', 'ip_address')

    def __str__(self):
        return f"{self.ip_address} ({self.hostname or 'Unknown'})"
