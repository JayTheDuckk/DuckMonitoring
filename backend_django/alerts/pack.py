from .models import AlertRule

HOST_DOWN_CONDITION = {"field": "status", "operator": "equals", "value": "critical"}

DEFAULT_PACK = (
    {
        'condition_type': 'host_down',
        'name': 'Host down',
        'severity': 'critical',
        'condition': HOST_DOWN_CONDITION,
    },
    {
        'condition_type': 'device_new',
        'name': 'New device',
        'severity': 'info',
        'condition': {},
    },
    {
        'condition_type': 'device_gone',
        'name': 'Device gone',
        'severity': 'warning',
        'condition': {},
    },
)


def ensure_default_alert_pack():
    """Create the global host-down / new-device / device-gone rules if missing."""
    rules = []
    for spec in DEFAULT_PACK:
        rule = AlertRule.objects.filter(
            condition_type=spec['condition_type'],
            host__isnull=True,
            host_group__isnull=True,
        ).first()
        if rule is None:
            rule = AlertRule.objects.create(
                name=spec['name'],
                condition_type=spec['condition_type'],
                condition=spec['condition'],
                severity=spec['severity'],
                host=None,
                host_group=None,
                enabled=True,
            )
        rules.append(rule)
    return rules
