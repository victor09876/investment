from django.core.management.base import BaseCommand
from django.utils import timezone
from investments.models import Investment
from transactions.models import Transaction
from accounts.models import Notification


class Command(BaseCommand):
    help = 'Credit daily ROI to all active investments (run daily via cron)'

    def handle(self, *args, **options):
        today = timezone.now().date()
        active = Investment.objects.filter(
            status='active', end_date__gt=timezone.now()
        ).exclude(last_roi_date=today).select_related('user', 'plan')

        credited = 0
        for inv in active:
            inv.user.profit_balance += inv.daily_profit
            inv.user.save(update_fields=['profit_balance'])
            inv.profit_earned += inv.daily_profit
            inv.last_roi_date = today
            inv.save(update_fields=['profit_earned', 'last_roi_date'])
            Transaction.objects.create(
                user=inv.user, type='roi', method='wallet',
                amount=inv.daily_profit, net_amount=inv.daily_profit,
                status='completed',
                description=f'{inv.plan.name} Daily ROI ({inv.plan.daily_roi}%)',
                investment=inv
            )
            credited += 1

        # Complete matured investments
        due = Investment.objects.filter(
            status='active', end_date__lte=timezone.now()
        ).select_related('user', 'plan')

        completed = 0
        for inv in due:
            inv.user.wallet_balance += inv.amount
            inv.user.save(update_fields=['wallet_balance'])
            inv.status = 'completed'
            inv.save(update_fields=['status'])
            Transaction.objects.create(
                user=inv.user, type='refund', method='wallet',
                amount=inv.amount, net_amount=inv.amount,
                status='completed',
                description=f'{inv.plan.name} — Principal Returned',
                investment=inv
            )
            Notification.objects.create(
                user=inv.user, type='investment',
                title=f'{inv.plan.name} Completed! 🎉',
                body=(
                    f'Your {inv.plan.name} has matured. '
                    f'Principal of ${inv.amount:,.2f} returned. '
                    f'Total profit earned: ${inv.profit_earned:,.2f}.'
                )
            )
            completed += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ ROI credited to {credited} investments. {completed} plans completed.'
        ))
