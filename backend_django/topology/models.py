from django.db import models
from inventory.models import Host

class NetworkLink(models.Model):
    LINK_TYPES = (
        ('physical', 'Physical'),
        ('logical', 'Logical'),
        ('wireless', 'Wireless'),
        ('virtual', 'Virtual'),
    )

    PROTOCOLS = (
        ('lldp', 'LLDP'),
        ('cdp', 'CDP'),
        ('ospf', 'OSPF'),
        ('arp', 'ARP'),
        ('static', 'Static'),
        ('unknown', 'Unknown'),
    )

    # Source is always a known device/host in our inventory
    source = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='source_links')
    
    # Target can be a known host, or just a MAC/IP if not yet managed
    target = models.ForeignKey(Host, on_delete=models.SET_NULL, null=True, blank=True, related_name='target_links')
    target_mac = models.CharField(max_length=17, blank=True, null=True, help_text="MAC address of target if unknown")
    target_ip = models.GenericIPAddressField(blank=True, null=True, help_text="IP address of target if unknown")
    target_interface = models.CharField(max_length=255, blank=True, null=True, help_text="Interface on target device")
    
    source_interface = models.CharField(max_length=255, blank=True, null=True, help_text="Interface on source device")
    
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default='physical')
    protocol = models.CharField(max_length=20, choices=PROTOCOLS, default='unknown')
    
    bandwidth = models.BigIntegerField(null=True, blank=True, help_text="Link speed in bps")
    
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('source', 'target', 'source_interface', 'target_interface')

    def __str__(self):
        target_name = self.target.hostname if self.target else (self.target_ip or self.target_mac or "Unknown")
        return f"{self.source.hostname} -> {target_name} ({self.protocol})"
