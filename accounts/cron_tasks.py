"""
Shared scheduled-task logic.

These functions are called both by:
  - the admin "Credit ROI Now" button (manual trigger)
  - the CronTickMiddleware (automatic trigger, every cron_interval_minutes)
  - the `python manage.py run_cron` management command (for real OS-level cron)
"""
from django.utils import timezone
from .models import SiteSettings, Notification, CronJobLog


def credit_daily_roi():
    """Credit daily ROI to active investments and complete matured ones.
    Returns (roi_count, completed_count)."""
    from investments.models import Investment
    from transactions.models import Transaction

    today = timezone.now().date()
    active = Investment.objects.filter(status='active', end_date__gt=timezone.now()) \
        .exclude(last_roi_date=today).select_related('user', 'plan')
    roi_count = 0
    for inv in active:
        inv.user.profit_balance += inv.daily_profit
        inv.user.save(update_fields=['profit_balance'])
        inv.profit_earned += inv.daily_profit
        inv.last_roi_date = today
        inv.save(update_fields=['profit_earned', 'last_roi_date'])
        Transaction.objects.create(
            user=inv.user, type='roi', method='wallet', amount=inv.daily_profit,
            net_amount=inv.daily_profit, status='completed',
            description=f'{inv.plan.name} Daily ROI ({inv.plan.daily_roi}%)', investment=inv)
        roi_count += 1

    due = Investment.objects.filter(status='active', end_date__lte=timezone.now()).select_related('user', 'plan')
    completed_count = 0
    for inv in due:
        inv.user.wallet_balance += inv.amount
        inv.user.save(update_fields=['wallet_balance'])
        inv.status = 'completed'
        inv.save(update_fields=['status'])
        Transaction.objects.create(
            user=inv.user, type='refund', method='wallet', amount=inv.amount,
            net_amount=inv.amount, status='completed',
            description=f'{inv.plan.name} Principal Returned', investment=inv)
        Notification.objects.create(
            user=inv.user, type='investment', title=f'{inv.plan.name} Completed!',
            body=f'Principal ${inv.amount:,.2f} returned. Total profit: ${inv.profit_earned:,.2f}.')
        completed_count += 1

    return roi_count, completed_count


def expire_stale_deposits():
    """Mark pending deposits past their expiry as 'expired'. Returns count expired."""
    from transactions.models import Transaction

    stale = Transaction.objects.filter(type='deposit', status='pending', expires_at__lt=timezone.now())
    count = 0
    for txn in stale:
        txn.status = 'expired'
        txn.save(update_fields=['status'])
        Notification.objects.create(
            user=txn.user, type='deposit', title='Deposit Request Expired',
            body=f'Your ${txn.amount:,.2f} deposit request (#{txn.txn_id}) has expired. Please submit a new deposit if you still wish to fund your account.')
        count += 1
    return count


def run_all_cron_tasks(trigger='manual'):
    """Run all scheduled tasks and log the result. Returns a summary dict."""
    roi_count, completed_count = credit_daily_roi()
    expired_count = expire_stale_deposits()

    settings_obj = SiteSettings.get()
    settings_obj.cron_last_tick = timezone.now()
    settings_obj.save(update_fields=['cron_last_tick'])

    log, _ = CronJobLog.objects.get_or_create(slug='credit_roi', defaults={'name': 'Credit Daily ROI'})
    log.last_run = timezone.now()
    log.status = 'success'
    log.success_count = (log.success_count or 0) + 1
    log.save(update_fields=['last_run', 'status', 'success_count'])

    log2, _ = CronJobLog.objects.get_or_create(slug='expire_deposits', defaults={'name': 'Expire Stale Deposits'})
    log2.last_run = timezone.now()
    log2.status = 'success'
    log2.success_count = (log2.success_count or 0) + 1
    log2.save(update_fields=['last_run', 'status', 'success_count'])

    return {
        'trigger': trigger,
        'roi_count': roi_count,
        'completed_count': completed_count,
        'expired_count': expired_count,
        'ran_at': timezone.now(),
    }


def cron_due():
    """Check whether the automatic cron tick is due based on cron_interval_minutes."""
    settings_obj = SiteSettings.get()
    if not settings_obj.cron_last_tick:
        return True
    elapsed = (timezone.now() - settings_obj.cron_last_tick).total_seconds() / 60
    return elapsed >= settings_obj.cron_interval_minutes
