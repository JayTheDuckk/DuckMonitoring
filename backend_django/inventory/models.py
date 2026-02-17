from django.db import models
from django.utils import timezone

class HostGroup(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#667eea')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Host(models.Model):
    STATUS_CHOICES = (
        ('up', 'Up'),
        ('down', 'Down'),
        ('unknown', 'Unknown'),
    )
    
    hostname = models.CharField(max_length=255, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True, null=True, help_text="Custom name for dashboard display")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True, help_text="MAC Address in XX:XX:XX:XX:XX:XX format")
    vendor = models.CharField(max_length=255, blank=True, null=True, help_text="Device Vendor (e.g. Apple, Ubiquiti)")
    agent_id = models.CharField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    group = models.ForeignKey(HostGroup, related_name='hosts', on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.SET_NULL, null=True, blank=True, help_text="Uplink device (e.g. Switch, Gateway, AP)")
    last_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname

class UPSDevice(models.Model):
    STATUS_CHOICES = (
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    )
    
    name = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField()
    model_key = models.CharField(max_length=100)
    snmp_community = models.CharField(max_length=255, default='public')
    snmp_version = models.IntegerField(default=2)
    snmp_port = models.IntegerField(default=161)
    
    # SNMP v3 Fields
    snmp_username = models.CharField(max_length=255, blank=True, null=True)
    snmp_security_level = models.CharField(max_length=20, default='noAuthNoPriv', choices=(
        ('noAuthNoPriv', 'noAuthNoPriv'),
        ('authNoPriv', 'authNoPriv'),
        ('authPriv', 'authPriv'),
    ))
    snmp_auth_protocol = models.CharField(max_length=10, default='MD5', choices=(('MD5', 'MD5'), ('SHA', 'SHA')))
    snmp_auth_key = models.CharField(max_length=255, blank=True, null=True)
    snmp_priv_protocol = models.CharField(max_length=10, default='DES', choices=(('DES', 'DES'), ('AES', 'AES')))
    snmp_priv_key = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    last_check = models.DateTimeField(null=True, blank=True)
    
    enabled = models.BooleanField(default=True)
    check_interval = models.IntegerField(default=60)
    timeout = models.IntegerField(default=10)
    
    location = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SNMPDevice(models.Model):
    STATUS_CHOICES = (
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    )
    
    name = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField()
    model_key = models.CharField(max_length=100)
    snmp_community = models.CharField(max_length=255, default='public')
    snmp_version = models.IntegerField(default=2)
    snmp_port = models.IntegerField(default=161)
    
    # SNMP v3 Fields
    snmp_username = models.CharField(max_length=255, blank=True, null=True)
    snmp_security_level = models.CharField(max_length=20, default='noAuthNoPriv', choices=(
        ('noAuthNoPriv', 'noAuthNoPriv'),
        ('authNoPriv', 'authNoPriv'),
        ('authPriv', 'authPriv'),
    ))
    snmp_auth_protocol = models.CharField(max_length=10, default='MD5', choices=(('MD5', 'MD5'), ('SHA', 'SHA')))
    snmp_auth_key = models.CharField(max_length=255, blank=True, null=True)
    snmp_priv_protocol = models.CharField(max_length=10, default='DES', choices=(('DES', 'DES'), ('AES', 'AES')))
    snmp_priv_key = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    last_check = models.DateTimeField(null=True, blank=True)
    last_output = models.TextField(blank=True, null=True)
    
    enabled = models.BooleanField(default=True)
    check_interval = models.IntegerField(default=60)
    timeout = models.IntegerField(default=10)
    
    monitored_metrics = models.JSONField(default=list, blank=True)
    
    location = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
