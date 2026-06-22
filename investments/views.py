from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Plan, Investment
from transactions.models import Transaction
from accounts.models import Notification, SiteSettings


@login_required
def plans_view(request):
    plans = Plan.objects.filter(is_active=True)
    return render(request, 'investments/plans.html', {'plans': plans})


@login_required
def invest_view(request, slug):
    plan    = get_object_or_404(Plan, slug=slug, is_active=True)
    settings = SiteSettings.get()
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount','0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('invest', slug=slug)

        if amount < plan.min_amount:
            messages.error(request, f'Minimum investment is ${plan.min_amount:,.2f}.')
            return redirect('invest', slug=slug)
        if plan.max_amount and amount > plan.max_amount:
            messages.error(request, f'Maximum investment is ${plan.max_amount:,.2f}.')
            return redirect('invest', slug=slug)
        if request.user.wallet_balance < amount:
            messages.error(request, 'Insufficient wallet balance. Please deposit funds first.')
            return redirect('deposit')

        user = request.user
        user.wallet_balance -= amount
        user.save(update_fields=['wallet_balance'])

        daily  = plan.daily_profit_for(amount)
        inv = Investment.objects.create(
            user=user, plan=plan, amount=amount,
            daily_profit=daily, end_date=timezone.now()+timedelta(days=plan.duration_days))

        Transaction.objects.create(user=user, type='investment', method='wallet',
            amount=amount, net_amount=amount, status='completed',
            description=f'{plan.name} Investment', investment=inv)

        # Referral bonus
        if user.referred_by:
            bonus = amount * plan.referral_bonus_pct / 100
            user.referred_by.profit_balance += bonus
            user.referred_by.save(update_fields=['profit_balance'])
            Transaction.objects.create(user=user.referred_by, type='referral', method='wallet',
                amount=bonus, net_amount=bonus, status='completed',
                description=f'Referral bonus from {user.full_name}', investment=inv)
            Notification.objects.create(user=user.referred_by, type='referral',
                title=f'Referral Bonus — ${bonus:.2f}',
                body=f'{user.full_name} invested ${amount:,.2f}. You earned ${bonus:.2f}!')

        Notification.objects.create(user=user, type='investment',
            title=f'{plan.name} Active!',
            body=f'Your ${amount:,.2f} investment is live. Daily earnings: ${daily:.2f}.')

        messages.success(request, f'Investment of ${amount:,.2f} in {plan.name} is now active!')
        return redirect('my_investments')

    daily_sample = plan.daily_profit_for(plan.min_amount)
    total_sample = plan.total_return_for(plan.min_amount)
    return render(request, 'investments/invest.html', {
        'plan': plan, 'daily_sample': daily_sample, 'total_sample': total_sample,
    })


@login_required
def my_investments_view(request):
    tab    = request.GET.get('tab','active')
    inv_qs = Investment.objects.filter(user=request.user).select_related('plan')
    active    = inv_qs.filter(status='active')
    completed = inv_qs.filter(status='completed')
    cancelled = inv_qs.filter(status='cancelled')
    from django.db.models import Sum
    stats = {
        'active_total':    active.aggregate(t=Sum('amount'))['t'] or 0,
        'completed_profit':completed.aggregate(t=Sum('profit_earned'))['t'] or 0,
        'cancelled_count': cancelled.count(),
        'total_profit':    inv_qs.aggregate(t=Sum('profit_earned'))['t'] or 0,
    }
    return render(request, 'investments/my_investments.html', {
        'active':active,'completed':completed,'cancelled':cancelled,'tab':tab,'stats':stats,
    })


@login_required
def cancel_investment_view(request, pk):
    inv = get_object_or_404(Investment, pk=pk, user=request.user, status='active')
    if request.method == 'POST':
        settings = SiteSettings.get()
        if not settings.allow_investment_cancellation:
            messages.error(request, 'Investment cancellations are currently disabled by the administrator.')
            return redirect('my_investments')
        fee_pct  = settings.cancellation_fee_pct / 100
        fee      = inv.amount * fee_pct
        refund   = inv.amount - fee
        inv.status = 'cancelled'
        inv.save(update_fields=['status'])
        request.user.wallet_balance += refund
        request.user.save(update_fields=['wallet_balance'])
        Transaction.objects.create(user=request.user, type='refund', method='wallet',
            amount=refund, net_amount=refund, status='completed',
            description=f'{inv.plan.name} Cancellation Refund', investment=inv)
        Notification.objects.create(user=request.user, type='investment',
            title='Investment Cancelled',
            body=f'{inv.plan.name} cancelled. ${refund:.2f} refunded (${fee:.2f} fee).')
        messages.info(request, f'Investment cancelled. ${refund:,.2f} refunded to your wallet.')
    return redirect('my_investments')


@login_required
def roi_calculator_view(request):
    plans  = Plan.objects.filter(is_active=True)
    result = None
    if request.method == 'POST':
        slug   = request.POST.get('plan_slug')
        try:
            amount = Decimal(request.POST.get('amount','0'))
            plan   = Plan.objects.get(slug=slug)
            result = {
                'plan':   plan,
                'amount': amount,
                'daily':  plan.daily_profit_for(amount),
                'total_profit': plan.total_profit_for(amount),
                'total_return': plan.total_return_for(amount),
                'maturity': (timezone.now()+timedelta(days=plan.duration_days)).strftime('%b %d, %Y'),
            }
        except Exception:
            messages.error(request, 'Invalid input.')
    return render(request, 'investments/calculator.html', {'plans':plans,'result':result})
