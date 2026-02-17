from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Adds role-based access and 2FA fields.
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('operator', 'Operator'),
        ('viewer', 'Viewer'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    
    # Two-Factor Authentication fields
    totp_secret = models.CharField(max_length=32, blank=True, null=True)
    totp_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list, blank=True)  # Using JSONField for array
    
    def __str__(self):
        return self.username

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
        
    def is_operator(self):
        return self.role in ['admin', 'operator'] or self.is_superuser

class AuditLog(models.Model):
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=50)
    resource_type = models.CharField(max_length=50, blank=True, null=True)
    resource_id = models.CharField(max_length=255, blank=True, null=True)
    resource_name = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
