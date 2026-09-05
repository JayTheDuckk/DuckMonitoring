import logging
import os
from collections import Counter

from celery import shared_task

from inventory.models import DeviceObservation, upsert_observation

logger = logging.getLogger(__name__)

DEFAULT_PASSIVE_NETWORK = '192.168.0.0/24'


def _resolve_passive_network():
    env_net = (os.environ.get('PASSIVE_COLLECT_NETWORK') or '').strip()
    if env_net:
        return env_net

    networks = (
        DeviceObservation.objects.exclude(last_network__isnull=True)
        .exclude(last_network='')
        .values_list('last_network', flat=True)
    )
    if networks:
        return Counter(networks).most_common(1)[0][0]
    return DEFAULT_PASSIVE_NETWORK


@shared_task(name='inventory.tasks.passive_collect')
def passive_collect():
    from core.utils.passive_collector import collect_passive_hosts

    network = _resolve_passive_network()
    try:
        hosts = collect_passive_hosts(network)
    except Exception as exc:
        logger.warning('passive_collect failed: %s', exc)
        return 0

    count = 0
    for host_info in hosts:
        try:
            upsert_observation(host_info, network)
            count += 1
        except Exception as exc:
            logger.warning(
                'passive_collect upsert failed for %s: %s',
                host_info.get('ip_address'),
                exc,
            )
    return count


from config.celery import app

app.conf.beat_schedule = {
    **(getattr(app.conf, 'beat_schedule', None) or {}),
    'passive-collect-lan': {
        'task': 'inventory.tasks.passive_collect',
        'schedule': 120.0,
    },
}
