from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.http import HttpResponseBadRequest
from django.urls import reverse
from decimal import Decimal
import json
import urllib.error
import urllib.parse
import urllib.request
from .models import Transaction, WalletAddress
from accounts.models import Notification, SiteSettings


PAYSTACK_BASE_URL = 'https://api.paystack.co'


def _paystack_request(path, secret_key, payload=None):
    url = f'{PAYSTACK_BASE_URL}{path}'
    headers = {
        'Authorization': f'Bearer {secret_key}',
        'Content-Type': 'application/json',
    }
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method='POST' if payload is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode('utf-8'))
            message = body.get('message') or str(exc)
        except Exception:
            message = str(exc)
        raise ValueError(message)
    except urllib.error.URLError as exc:
        raise ValueError(f'Unable to contact Paystack: {exc.reason}')


def _credit_confirmed_deposit(txn):
    if txn.status == 'completed':
        return False

    txn.status = 'completed'
    from django.utils import timezone
    txn.processed_at = timezone.now()
    txn.save(update_fields=['status', 'processed_at'])

    user = txn.user
    user.wallet_balance += txn.net_amount
    user.save(update_fields=['wallet_balance'])

    Notification.objects.create(
        user=user,
        type='deposit',
        title=f'Deposit Confirmed - ${txn.amount:,.2f}',
        body=f'Your ${txn.amount:,.2f} deposit has been credited to your wallet.',
    )

    site = SiteSettings.get()
    if site.allow_deposit_referral_bonus and user.referred_by:
        ref_bonus = txn.amount * site.deposit_referral_bonus_pct / 100
        referrer = user.referred_by
        referrer.profit_balance += ref_bonus
        referrer.save(update_fields=['profit_balance'])
        Transaction.objects.create(
            user=referrer,
            type='referral',
            method='wallet',
            amount=ref_bonus,
            net_amount=ref_bonus,
            status='completed',
            description=f'Referral deposit bonus from {user.full_name} ({site.deposit_referral_bonus_pct}%)',
        )
        Notification.objects.create(
            user=referrer,
            type='referral',
            title=f'Referral Bonus - ${ref_bonus:,.2f}',
            body=f'You earned ${ref_bonus:,.2f} because {user.full_name} made a deposit.',
        )
    return True


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

        if method == 'paystack':
            if not settings.paystack_enabled or not settings.paystack_secret_key:
                messages.error(request, 'Paystack deposits are not available right now. Please choose another method.')
                return redirect('deposit')

            txn = Transaction.objects.create(
                user=request.user, type='deposit', method=method,
                amount=amount, fee=0, net_amount=amount, status='pending',
                description='Paystack Deposit', expires_at=expires_at)
            txn.reference = txn.txn_id
            txn.save(update_fields=['reference'])

            callback_url = request.build_absolute_uri(reverse('paystack_callback'))
            payload = {
                'email': request.user.email,
                'amount': int((amount * Decimal('100')).quantize(Decimal('1'))),
                'currency': (settings.paystack_currency or 'NGN').upper(),
                'reference': txn.reference,
                'callback_url': callback_url,
                'metadata': {
                    'transaction_id': str(txn.id),
                    'user_id': str(request.user.id),
                },
            }
            try:
                response = _paystack_request('/transaction/initialize', settings.paystack_secret_key, payload)
                auth_url = response.get('data', {}).get('authorization_url')
                if not response.get('status') or not auth_url:
                    raise ValueError(response.get('message') or 'Paystack did not return a checkout URL.')
            except ValueError as exc:
                txn.status = 'failed'
                txn.description = f'Paystack Deposit Failed: {exc}'
                txn.save(update_fields=['status', 'description'])
                messages.error(request, f'Unable to start Paystack payment: {exc}')
                return redirect('deposit')

            Notification.objects.create(user=request.user, type='deposit',
                title='Paystack Payment Started',
                body=f'Complete your {settings.paystack_currency} payment on Paystack to fund your wallet.')
            return redirect(auth_url)

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


def paystack_callback_view(request):
    reference = request.GET.get('reference', '').strip()
    if not reference:
        return HttpResponseBadRequest('Missing Paystack reference.')

    settings = SiteSettings.get()
    if not settings.paystack_enabled or not settings.paystack_secret_key:
        messages.error(request, 'Paystack is not configured.')
        return redirect('deposit')

    try:
        response = _paystack_request(f'/transaction/verify/{urllib.parse.quote(reference)}', settings.paystack_secret_key)
    except ValueError as exc:
        messages.error(request, f'Unable to verify Paystack payment: {exc}')
        return redirect('transactions')

    data = response.get('data') or {}
    if not response.get('status') or data.get('status') != 'success':
        messages.error(request, 'Paystack payment was not successful.')
        return redirect('transactions')

    with db_transaction.atomic():
        txn = get_object_or_404(
            Transaction.objects.select_for_update().select_related('user'),
            reference=reference,
            type='deposit',
            method='paystack',
        )
        if txn.status == 'completed':
            credited = False
        else:
            expected_amount = int((txn.amount * Decimal('100')).quantize(Decimal('1')))
            paid_amount = int(data.get('amount') or 0)
            paid_currency = (data.get('currency') or '').upper()
            expected_currency = (settings.paystack_currency or 'NGN').upper()
            if paid_amount < expected_amount or paid_currency != expected_currency:
                txn.status = 'failed'
                txn.description = 'Paystack verification failed: amount or currency mismatch'
                txn.save(update_fields=['status', 'description'])
                messages.error(request, 'Payment verification failed because the amount or currency did not match.')
                return redirect('transactions')

            credited = _credit_confirmed_deposit(txn)

    if credited:
        messages.success(request, f'Paystack payment confirmed. ${txn.amount:,.2f} has been added to your wallet.')
    else:
        messages.info(request, 'This Paystack payment was already confirmed.')
    return redirect('transactions')


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
