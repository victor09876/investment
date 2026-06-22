from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Transaction, WalletAddress
from accounts.models import Notification, SiteSettings


@login_required
def deposit_view(request):
    settings = SiteSettings.get()
    wallets  = WalletAddress.objects.filter(is_active=True)
    wallet_map = {w.coin: w.address for w in wallets}

    if settings.require_kyc_deposit and not request.user.is_kyc_verified:
        messages.error(request, 'KYC verification is required before making a deposit.')
        return redirect('kyc')

    if request.method == 'POST':
        method = request.POST.get('method','')
        try:
            amount = Decimal(request.POST.get('amount','0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('deposit')
        if amount < settings.min_deposit:
            messages.error(request, f'Minimum deposit is ${settings.min_deposit}.')
            return redirect('deposit')

        from django.utils import timezone
        from datetime import timedelta
        expires_at = timezone.now() + timedelta(minutes=settings.deposit_timeout_minutes)

        if method == 'credit_card':
            card_brand = request.POST.get('card_brand','').strip()
            txn = Transaction.objects.create(
                user=request.user, type='deposit', method=method,
                amount=amount, fee=0, net_amount=amount, status='pending',
                description=f'Card Deposit ({card_brand.title()})' if card_brand else 'Card Deposit',
                card_brand=card_brand, expires_at=expires_at)
        else:
            reference   = request.POST.get('reference','').strip()
            proof_image = request.FILES.get('proof_image')
            txn = Transaction.objects.create(
                user=request.user, type='deposit', method=method,
                amount=amount, fee=0, net_amount=amount, status='pending',
                description=f'{method.replace("_"," ").title()} Deposit',
                reference=reference, expires_at=expires_at)
            if proof_image:
                txn.proof_image = proof_image
                txn.save(update_fields=['proof_image'])

        Notification.objects.create(user=request.user, type='deposit',
            title='Deposit Request Submitted',
            body=f'Your ${amount:,.2f} deposit is pending admin approval. Complete payment within {settings.deposit_timeout_minutes} minutes.')
        messages.success(request, f'Deposit request submitted! Your ${amount:,.2f} will be credited after confirmation.')
        return redirect('transactions')

    return render(request, 'transactions/deposit.html', {
        'settings': settings, 'wallet_map': wallet_map,
        'recent': Transaction.objects.filter(user=request.user, type='deposit').order_by('-created_at')[:5],
    })


@login_required
def withdrawal_view(request):
    settings = SiteSettings.get()
    user     = request.user

    if settings.require_kyc_withdraw and not user.is_kyc_verified:
        messages.error(request, 'KYC verification is required before making a withdrawal.')
        return redirect('kyc')

    if request.method == 'POST':
        method      = request.POST.get('method','')
        destination = request.POST.get('destination','').strip()
        pin         = request.POST.get('pin','').strip()
        source      = request.POST.get('source','wallet')
        if source not in ('wallet', 'profit'):
            source = 'wallet'
        try:
            amount = Decimal(request.POST.get('amount','0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('withdrawal')

        if amount < settings.min_withdrawal:
            messages.error(request, f'Minimum withdrawal is ${settings.min_withdrawal}.')
            return redirect('withdrawal')
        if not user.withdrawal_pin:
            messages.error(request, 'Please set a withdrawal PIN in Settings first.')
            return redirect('set_pin')
        if not user.check_withdrawal_pin(pin):
            messages.error(request, 'Incorrect withdrawal PIN.')
            return redirect('withdrawal')

        source_balance = user.wallet_balance if source == 'wallet' else user.profit_balance
        if source_balance < amount:
            messages.error(request, f'Insufficient {"wallet" if source == "wallet" else "profit"} balance.')
            return redirect('withdrawal')
        if not destination:
            messages.error(request, 'Please enter your withdrawal destination.')
            return redirect('withdrawal')

        fee    = amount * settings.withdrawal_fee_pct / 100
        net    = amount - fee
        if source == 'wallet':
            user.wallet_balance -= amount
            user.save(update_fields=['wallet_balance'])
        else:
            user.profit_balance -= amount
            user.save(update_fields=['profit_balance'])
        txn = Transaction.objects.create(
            user=user, type='withdrawal', method=method,
            amount=amount, fee=fee, net_amount=net, status='processing',
            description=f'{method.replace("_"," ").title()} Withdrawal ({"Profit" if source == "profit" else "Wallet"})',
            destination=destination)
        Notification.objects.create(user=user, type='withdrawal',
            title=f'Withdrawal Processing — ${amount:,.2f}',
            body=f'Your ${amount:,.2f} withdrawal from your {"profit" if source == "profit" else "wallet"} balance to {destination[:40]} is being processed.')
        messages.success(request, f'Withdrawal of ${amount:,.2f} submitted and is being processed.')
        return redirect('transactions')

    return render(request, 'transactions/withdrawal.html', {
        'settings': settings, 'user': user,
        'recent': Transaction.objects.filter(user=user, type='withdrawal').order_by('-created_at')[:5],
    })


@login_required
def transactions_view(request):
    user = request.user
    qs   = Transaction.objects.filter(user=user)
    txn_type   = request.GET.get('type','')
    txn_status = request.GET.get('status','')
    search     = request.GET.get('q','')
    date_from  = request.GET.get('from','')
    date_to    = request.GET.get('to','')

    if txn_type:   qs = qs.filter(type=txn_type)
    if txn_status: qs = qs.filter(status=txn_status)
    if search:     qs = qs.filter(Q(txn_id__icontains=search)|Q(description__icontains=search))
    if date_from:  qs = qs.filter(created_at__date__gte=date_from)
    if date_to:    qs = qs.filter(created_at__date__lte=date_to)

    summary = Transaction.objects.filter(user=user).aggregate(
        deposited=Sum('amount', filter=Q(type='deposit',status='completed')),
        withdrawn=Sum('amount', filter=Q(type='withdrawal',status='completed')),
        earned=Sum('amount', filter=Q(type='roi',status='completed')),
    )
    return render(request, 'transactions/transactions.html', {
        'transactions': qs, 'summary': summary,
        'filter': {'type':txn_type,'status':txn_status,'q':search,'from':date_from,'to':date_to},
    })
