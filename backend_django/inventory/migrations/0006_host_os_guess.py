from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_host_identity_and_deviceobservation'),
    ]

    operations = [
        migrations.AddField(
            model_name='deviceobservation',
            name='os_guess',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='host',
            name='os_guess',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
