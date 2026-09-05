from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from config.celery import app

app.conf.beat_schedule = {
    **(getattr(app.conf, 'beat_schedule', None) or {}),
    'evaluate-inventory-events': {
        'task': 'alerts.tasks.evaluate_inventory_events',
        'schedule': 300.0,
    },
}


@shared_task(name='alerts.tasks.evaluate_inventory_events')
def evaluate_inventory_events():
    """Fire default-pack alerts for newly seen and stale LAN observations."""
    from inventory.models import DeviceObservation

    from .models import AlertRule
    from .pack import ensure_default_alert_pack
    from .services import AlertService

    ensure_default_alert_pack()
    now = timezone.now()

    new_rule = AlertRule.objects.filter(
        condition_type='device_new',
        host__isnull=True,
        host_group__isnull=True,
        enabled=True,
    ).first()
    gone_rule = AlertRule.objects.filter(
        condition_type='device_gone',
        host__isnull=True,
        host_group__isnull=True,
        enabled=True,
    ).first()

    if new_rule:
        fresh_cutoff = now - timedelta(minutes=10)
        for observation in DeviceObservation.objects.filter(first_seen__gte=fresh_cutoff):
            AlertService.fire_inventory_event(
                new_rule,
                observation,
                title=f"New device: {observation.mdns_name or observation.hostname or observation.ip_address}",
                message=(
                    f"Device {observation.mdns_name or observation.hostname or observation.ip_address} "
                    f"({observation.ip_address}) first seen on the network."
                ),
            )

    if gone_rule:
        stale_cutoff = now - timedelta(hours=24)
        for observation in DeviceObservation.objects.filter(last_seen__lt=stale_cutoff):
            AlertService.fire_inventory_event(
                gone_rule,
                observation,
                title=f"Device gone: {observation.mdns_name or observation.hostname or observation.ip_address}",
                message=(
                    f"Device {observation.mdns_name or observation.hostname or observation.ip_address} "
                    f"({observation.ip_address}) has not been seen in over 24 hours."
                ),
            )
