import ipaddress

from django.db import models
from django.utils import timezone

CONFIDENCE_SCORES = {
    'high': 80,
    'medium': 50,
    'low': 20,
}


def _nonempty(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if value in ([], {}, ()):
        return None
    return value


def normalize_confidence(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        key = value.lower().strip()
        if key in CONFIDENCE_SCORES:
            return CONFIDENCE_SCORES[key]
        try:
            return int(key)
        except ValueError:
            return None
    return None


def _prefer(new_value, old_value):
    kept = _nonempty(new_value)
    if kept is not None:
        return kept
    return old_value


def _richer_confidence(new_value, old_value):
    new_score = normalize_confidence(new_value)
    old_score = normalize_confidence(old_value)
    if new_score is None:
        return old_score
    if old_score is None:
        return new_score
    return new_score if new_score >= old_score else old_score


def apply_host_identity(host, host_info, now=None, *, created=False):
    now = now or timezone.now()
    incoming_hostname = _nonempty(host_info.get('mdns_name')) or _nonempty(host_info.get('hostname'))
    if incoming_hostname:
        host.hostname = incoming_hostname
    elif created and not host.hostname:
        host.hostname = host_info.get('ip_address') or host.ip_address

    incoming_mdns = _nonempty(host_info.get('mdns_name'))
    if incoming_mdns:
        host.mdns_name = incoming_mdns

    incoming_apple = _nonempty(host_info.get('apple_model'))
    if incoming_apple:
        host.apple_model = incoming_apple

    incoming_class = _nonempty(host_info.get('device_class'))
    if incoming_class:
        host.device_class = incoming_class

    confidence = normalize_confidence(host_info.get('confidence'))
    if confidence is not None:
        host.confidence = confidence

    clues = host_info.get('identification_clues')
    if clues:
        host.identification_clues = clues

    if not host.first_seen:
        host.first_seen = now
    host.last_seen = now
    return host


def observation_matches_network(observation, network):
    if observation.last_network and observation.last_network == network:
        return True
    if not network or not observation.ip_address:
        return False
    try:
        ip = ipaddress.ip_address(observation.ip_address)
        if '/' in network:
            return ip in ipaddress.ip_network(network, strict=False)
        from inventory.discovery import parse_network_range
        return str(ip) in set(parse_network_range(network))
    except (ValueError, TypeError):
        return False


def observation_as_host(observation, seen_this_scan=False):
    payload = dict(observation.last_payload or {})
    payload['ip_address'] = observation.ip_address
    payload['mac_address'] = observation.mac_address or payload.get('mac_address')
    payload['hostname'] = observation.hostname or payload.get('hostname')
    payload['mdns_name'] = observation.mdns_name or payload.get('mdns_name')
    payload['apple_model'] = observation.apple_model or payload.get('apple_model')
    payload['device_class'] = observation.device_class or payload.get('device_class')
    payload['vendor'] = observation.vendor or payload.get('vendor')
    payload['vendor_source'] = observation.vendor_source or payload.get('vendor_source')
    if observation.identification_clues:
        payload['identification_clues'] = observation.identification_clues
    if observation.confidence is not None:
        payload.setdefault('confidence', observation.confidence)
    payload['first_seen'] = observation.first_seen.isoformat() if observation.first_seen else None
    payload['last_seen'] = observation.last_seen.isoformat() if observation.last_seen else None
    payload['seen_this_scan'] = seen_this_scan
    return payload


def upsert_observation(host_info, network, now=None):
    now = now or timezone.now()
    ip = host_info.get('ip_address')
    if not ip:
        raise ValueError('host_info requires ip_address')

    observation = DeviceObservation.objects.filter(ip_address=ip).first()
    if observation is None:
        observation = DeviceObservation(
            ip_address=ip,
            first_seen=now,
            sighting_count=0,
        )

    new_mac = _nonempty(host_info.get('mac_address'))
    if new_mac:
        observation.mac_address = new_mac

    observation.hostname = _prefer(host_info.get('hostname'), observation.hostname)
    observation.mdns_name = _prefer(host_info.get('mdns_name'), observation.mdns_name)
    observation.apple_model = _prefer(host_info.get('apple_model'), observation.apple_model)
    observation.device_class = _prefer(host_info.get('device_class'), observation.device_class)
    observation.confidence = _richer_confidence(host_info.get('confidence'), observation.confidence)
    clues = host_info.get('identification_clues')
    if clues:
        observation.identification_clues = clues
    observation.vendor = _prefer(host_info.get('vendor'), observation.vendor)
    observation.vendor_source = _prefer(host_info.get('vendor_source'), observation.vendor_source)
    observation.last_payload = dict(host_info)
    if not observation.first_seen:
        observation.first_seen = now
    observation.last_seen = now
    observation.last_network = network
    observation.sighting_count = (observation.sighting_count or 0) + 1
    observation.save()
    return observation

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
    mdns_name = models.CharField(max_length=255, blank=True, null=True)
    apple_model = models.CharField(max_length=255, blank=True, null=True)
    device_class = models.CharField(max_length=64, blank=True, null=True)
    confidence = models.IntegerField(null=True, blank=True)
    identification_clues = models.JSONField(default=list, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    agent_id = models.CharField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    group = models.ForeignKey(HostGroup, related_name='hosts', on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.SET_NULL, null=True, blank=True, help_text="Uplink device (e.g. Switch, Gateway, AP)")
    last_check = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hostname

    def update_status(self):
        """Update host status based on service checks."""
        from monitoring.models import ServiceCheckConfig
        
        ping_checks = ServiceCheckConfig.objects.filter(
            host=self,
            check_type='ping',
            enabled=True
        )
        
        if ping_checks.exists():
            ping_status = ping_checks.first().status
            if ping_status == 'ok':
                self.status = 'up'
            elif ping_status == 'critical':
                self.status = 'down'
            else:
                self.status = 'unknown'
        else:
            all_checks = ServiceCheckConfig.objects.filter(host=self, enabled=True)
            if all_checks.exists():
                has_ok = all_checks.filter(status='ok').exists()
                all_critical = all_checks.exclude(status='critical').count() == 0
                if has_ok:
                    self.status = 'up'
                elif all_critical and all_checks.count() > 0:
                    self.status = 'down'
                else:
                    self.status = 'unknown'
        
        self.last_check = timezone.now()
        self.save()


class DeviceObservation(models.Model):
    ip_address = models.GenericIPAddressField(db_index=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True, db_index=True)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    mdns_name = models.CharField(max_length=255, blank=True, null=True)
    apple_model = models.CharField(max_length=255, blank=True, null=True)
    device_class = models.CharField(max_length=64, blank=True, null=True)
    confidence = models.IntegerField(null=True, blank=True)
    identification_clues = models.JSONField(default=list, blank=True)
    vendor = models.CharField(max_length=255, blank=True, null=True)
    vendor_source = models.CharField(max_length=64, blank=True, null=True)
    last_payload = models.JSONField(default=dict, blank=True)
    first_seen = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_network = models.CharField(max_length=64, blank=True, null=True)
    sighting_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['ip_address'], name='uniq_device_observation_ip'),
        ]

    def __str__(self):
        return self.ip_address


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
