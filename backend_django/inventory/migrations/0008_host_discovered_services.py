from django.db import migrations, models


def copy_services_from_observations(apps, schema_editor):
    Host = apps.get_model('inventory', 'Host')
    DeviceObservation = apps.get_model('inventory', 'DeviceObservation')
    observations = {
        item.ip_address: item
        for item in DeviceObservation.objects.exclude(last_payload={})
    }
    for host in Host.objects.all():
        payload = (observations.get(host.ip_address).last_payload if observations.get(host.ip_address) else None) or {}
        services = payload.get('services') or []
        if services:
            host.discovered_services = services
            host.save(update_fields=['discovered_services'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0007_lanwatchsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='discovered_services',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(copy_services_from_observations, migrations.RunPython.noop),
    ]
