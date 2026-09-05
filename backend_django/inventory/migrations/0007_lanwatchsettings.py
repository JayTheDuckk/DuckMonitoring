from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_host_os_guess'),
    ]

    operations = [
        migrations.CreateModel(
            name='LanWatchSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_add_hosts', models.BooleanField(default=False)),
                ('network', models.CharField(blank=True, default='', max_length=64)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
