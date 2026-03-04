import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from monitoring.models import Metric, ServiceCheckResult

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Cleans up metrics and service check results older than a specified number of days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to keep historical metrics (default: 30)'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        self.stdout.write(self.style.WARNING(f"Deleting historical data older than {days_to_keep} days ({cutoff_date})..."))

        # Clean up specific models
        metrics_deleted, _ = Metric.objects.filter(timestamp__lt=cutoff_date).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {metrics_deleted} old Metrics."))

        checks_deleted, _ = ServiceCheckResult.objects.filter(timestamp__lt=cutoff_date).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {checks_deleted} old ServiceCheckResults."))

        self.stdout.write(self.style.SUCCESS("Cleanup database operation complete."))
