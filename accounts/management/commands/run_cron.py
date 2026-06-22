from django.core.management.base import BaseCommand
from accounts.cron_tasks import run_all_cron_tasks


class Command(BaseCommand):
    help = 'Run scheduled tasks: credit daily ROI, complete matured investments, expire stale deposits. Intended to be run every 5 minutes via OS cron.'

    def handle(self, *args, **options):
        result = run_all_cron_tasks(trigger='os_cron')
        self.stdout.write(self.style.SUCCESS(
            f"Cron run complete: {result['roi_count']} ROI credited, "
            f"{result['completed_count']} investments completed, "
            f"{result['expired_count']} deposits expired."
        ))
