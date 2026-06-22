from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q as DjQ
from .models import User, Notification, SiteSettings, RegistrationCode
from .forms import RegisterForm, LoginForm, ProfileForm, ChangePasswordForm, WithdrawalPINForm
from investments.models import Investment, Plan
from transactions.models import Transaction
from decimal import Decimal


def register_view(request):
    settings = SiteSettings.get()
    referred_by_user = None
    ref_code_param = request.GET.get('ref','')
    if ref_code_param:
        referred_by_user = User.objects.filter(referral_code=ref_code_param).first()

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Check registration code if required
            if settings.require_reg_code:
                code_val = form.cleaned_data.get('reg_code','').strip()
                try:
                    code_obj = RegistrationCode.objects.get(code=code_val)
                    if not code_obj.is_valid():
                        form.add_error('reg_code', 'This registration code is invalid or expired.')
                        return render(request, 'accounts/register.html', {'form': form, 'settings': settings, 'referred_by_user': referred_by_user})
                except RegistrationCode.DoesNotExist:
                    form.add_error('reg_code', 'Invalid registration code.')
                    return render(request, 'accounts/register.html', {'form': form, 'settings': settings, 'referred_by_user': referred_by_user})
            else:
                code_obj = None

            # Referral
            ref_code = request.GET.get('ref') or request.POST.get('referral_code_display','')
            referred_by = None
            if ref_code:
                try: referred_by = User.objects.get(referral_code=ref_code)
                except User.DoesNotExist: pass

            user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data.get('phone',''),
                country=form.cleaned_data.get('country',''),
                state=form.cleaned_data.get('state',''),
                dial_code=form.cleaned_data.get('dial_code',''),
                referred_by=referred_by,
            )
            if settings.welcome_bonus > 0:
                user.wallet_balance = settings.welcome_bonus
                user.save(update_fields=['wallet_balance'])
                Transaction.objects.create(user=user, type='deposit', method='wallet',
                    amount=settings.welcome_bonus, net_amount=settings.welcome_bonus,
                    status='completed', description='Welcome Bonus')
            if code_obj:
                code_obj.use()
            Notification.objects.create(user=user, type='system',
                title='Welcome to InvestPro! 🎉',
                body=f'Hi {user.first_name}, your account is ready. Start investing today!')
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form, 'settings': settings, 'referred_by_user': referred_by_user})


# login_view moved below — see overridden version with login history recording


def logout_view(request):
    logout(request)
    return redirect('login')


def forgot_password_view(request):
    sent = False
    if request.method == 'POST':
        email = request.POST.get('email','').strip().lower()
        user = User.objects.filter(email=email).first()
        if user:
            from .models import PasswordResetToken
            from .email_utils import send_email
            reset_token = PasswordResetToken.generate(user)
            reset_url = request.build_absolute_uri(f'/reset-password/{reset_token.token}/')
            send_email(user.email, 'Reset your password', 'password_reset',
                       {'user': user, 'reset_url': reset_url})
        sent = True
        messages.success(request, 'If that email exists, a password reset link has been sent.')
    return render(request, 'accounts/forgot_password.html', {'sent': sent})


def reset_password_view(request, token):
    from .models import PasswordResetToken
    reset_token = PasswordResetToken.objects.filter(token=token).first()
    if not reset_token or not reset_token.is_valid():
        messages.error(request, 'This password reset link is invalid or has expired. Please request a new one.')
        return redirect('forgot_password')

    if request.method == 'POST':
        pw1 = request.POST.get('password','')
        pw2 = request.POST.get('password2','')
        if len(pw1) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        elif pw1 != pw2:
            messages.error(request, 'Passwords do not match.')
        else:
            user = reset_token.user
            user.set_password(pw1)
            user.save(update_fields=['password'])
            reset_token.used = True
            reset_token.save(update_fields=['used'])
            Notification.objects.create(user=user, type='security',
                title='Password Changed', body='Your password was reset successfully.')
            messages.success(request, 'Your password has been reset. You can now log in.')
            return redirect('login')

    return render(request, 'accounts/reset_password.html', {'token': token})


@login_required
def dashboard_view(request):
    user = request.user
    active_investments = Investment.objects.filter(user=user, status='active').select_related('plan')
    recent_txns = Transaction.objects.filter(user=user).order_by('-created_at')[:6]
    stats = {
        'wallet_balance':  user.wallet_balance,
        'profit_balance':  user.profit_balance,
        'total_balance':   user.total_balance,
        'total_profit':    Transaction.objects.filter(user=user, type='roi', status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'active_count':    active_investments.count(),
        'referral_earn':   Transaction.objects.filter(user=user, type='referral', status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'total_deposited': Transaction.objects.filter(user=user, type='deposit', status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'total_withdrawn': Transaction.objects.filter(user=user, type='withdrawal', status='completed').aggregate(t=Sum('amount'))['t'] or 0,
    }
    monthly = []
    from django.utils import timezone
    from datetime import timedelta
    for i in range(5, -1, -1):
        d = timezone.now() - timedelta(days=30*i)
        amt = Transaction.objects.filter(user=user, type='roi', status='completed',
            created_at__year=d.year, created_at__month=d.month).aggregate(t=Sum('amount'))['t'] or 0
        monthly.append({'month': d.strftime('%b'), 'amount': float(amt)})
    unread_count = Notification.objects.filter(user=user, is_read=False).count()
    return render(request, 'accounts/dashboard.html', {
        'stats': stats, 'active_investments': active_investments,
        'recent_txns': recent_txns, 'monthly': monthly, 'unread_count': unread_count,
    })


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)
    inv_stats = Investment.objects.filter(user=user).aggregate(count=Count('id'), total=Sum('amount'))
    return render(request, 'accounts/profile.html', {'form': form, 'inv_stats': inv_stats})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user = request.user
            if not user.check_password(form.cleaned_data['current_password']):
                messages.error(request, 'Current password is incorrect.')
            else:
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                update_session_auth_hash(request, user)
                Notification.objects.create(user=user, type='security',
                    title='Password Changed', body='Your password was changed successfully.')
                messages.success(request, 'Password changed successfully.')
                return redirect('profile')
    else:
        form = ChangePasswordForm()
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def set_pin_view(request):
    if request.method == 'POST':
        form = WithdrawalPINForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.withdrawal_pin:
                if not user.check_withdrawal_pin(form.cleaned_data.get('current_pin','')):
                    messages.error(request, 'Current PIN is incorrect.')
                    return render(request, 'accounts/set_pin.html', {'form': form})
            user.set_withdrawal_pin(form.cleaned_data['new_pin'])
            user.save()
            messages.success(request, 'Withdrawal PIN set successfully.')
            return redirect('settings')
    else:
        form = WithdrawalPINForm()
    return render(request, 'accounts/set_pin.html', {'form': form})


@login_required
def notifications_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_all':
            Notification.objects.filter(user=request.user).update(is_read=True)
        elif action == 'mark_one':
            nid = request.POST.get('id')
            Notification.objects.filter(user=request.user, id=nid).update(is_read=True)
        return redirect('notifications')
    notifs = Notification.objects.filter(user=request.user)
    unread_count = notifs.filter(is_read=False).count()
    return render(request, 'accounts/notifications.html', {'notifs': notifs, 'unread_count': unread_count})


@login_required
def settings_view(request):
    return render(request, 'accounts/settings.html', {'user': request.user})


# ─────────────────────────────────────────────
# HELPER: Record login
# ─────────────────────────────────────────────
def record_login(request, user, status='success'):
    try:
        from .models import LoginHistory
        import user_agents as ua_lib
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        ua = ua_lib.parse(ua_string)
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        if ',' in ip: ip = ip.split(',')[0].strip()

        device_type = 'mobile' if ua.is_mobile else ('tablet' if ua.is_tablet else 'pc')

        # Check if new device
        is_new = not LoginHistory.objects.filter(user=user, ip_address=ip).exists()

        history = LoginHistory.objects.create(
            user=user, ip_address=ip, user_agent=ua_string,
            browser=ua.browser.family, browser_ver=ua.browser.version_string,
            os=ua.os.family, os_ver=ua.os.version_string,
            device=ua.device.family, device_type=device_type,
            status=status, is_new_device=is_new,
        )
        if is_new and status == 'success':
            Notification.objects.create(
                user=user, type='security',
                title='New Login Detected',
                body=f'Login from {ua.browser.family} on {ua.os.family} ({ip}). If this was not you, secure your account immediately.'
            )
    except Exception:
        pass


# ─────────────────────────────────────────────
# OVERRIDDEN LOGIN to record history
# ─────────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email    = request.POST.get('email','').strip()
        password = request.POST.get('password','')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            record_login(request, user, 'success')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            # Try to find the user to record failed attempt
            try:
                failed_user = User.objects.get(email=email)
                record_login(request, failed_user, 'failed')
            except User.DoesNotExist:
                pass
            messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html')


# ─────────────────────────────────────────────
# LOGIN HISTORY VIEW
# ─────────────────────────────────────────────
@login_required
def login_history_view(request):
    from .models import LoginHistory
    history = LoginHistory.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'accounts/login_history.html', {'history': history})


# ─────────────────────────────────────────────
# NOTIFICATIONS API
# ─────────────────────────────────────────────
from django.http import JsonResponse

@login_required
def notifications_api(request):
    FA_ICONS = {
        'roi': 'fa-coins', 'deposit': 'fa-credit-card', 'withdrawal': 'fa-money-bill-wave',
        'investment': 'fa-chart-line', 'referral': 'fa-users', 'security': 'fa-shield-halved',
        'promo': 'fa-gift', 'system': 'fa-bell',
    }
    notifs = Notification.objects.filter(user=request.user)[:10]
    data = [{
        'id': str(n.id), 'title': n.title, 'body': n.body,
        'is_read': n.is_read, 'type': n.type,
        'icon': FA_ICONS.get(n.type, 'fa-bell'),
        'time': n.created_at.strftime('%b %d, %H:%M'),
    } for n in notifs]
    return JsonResponse({'notifications': data})


# ─────────────────────────────────────────────
# KYC
# ─────────────────────────────────────────────
@login_required
def kyc_view(request):
    from .models import KYCField, KYCSubmission, KYCAnswer
    fields = KYCField.objects.filter(is_active=True).order_by('sort_order')
    submission = KYCSubmission.objects.filter(user=request.user).first()

    if request.method == 'POST' and not (submission and submission.status == 'approved'):
        if not submission:
            submission = KYCSubmission.objects.create(user=request.user)
        else:
            submission.status = 'pending'
            submission.save(update_fields=['status'])

        for field in fields:
            answer, _ = KYCAnswer.objects.get_or_create(submission=submission, field=field)
            if field.field_type in ('file', 'image'):
                if f'field_{field.id}' in request.FILES:
                    answer.file_value = request.FILES[f'field_{field.id}']
            else:
                answer.value = request.POST.get(f'field_{field.id}', '')
            answer.save()

        Notification.objects.create(user=request.user, type='system',
            title='KYC Submitted', body='Your KYC documents have been submitted and are under review.')
        request.user.kyc_status = 'submitted'
        request.user.save(update_fields=['kyc_status'])
        messages.success(request, 'KYC documents submitted successfully. Awaiting review.')
        return redirect('kyc')

    answers = {}
    if submission:
        for a in KYCAnswer.objects.filter(submission=submission).select_related('field'):
            answers[str(a.field.id)] = a

    return render(request, 'accounts/kyc.html', {
        'fields': fields, 'submission': submission, 'answers': answers,
    })


# ─────────────────────────────────────────────
# REFERRALS
# ─────────────────────────────────────────────
@login_required
def referrals_view(request):
    user = request.user
    from transactions.models import Transaction
    referrals = User.objects.filter(referred_by=user).order_by('-date_joined')
    earnings  = Transaction.objects.filter(user=user, type='referral', status='completed')
    from django.db.models import Sum
    total_earn= earnings.aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'accounts/referrals.html', {
        'referrals': referrals, 'total_earn': total_earn, 'earnings': earnings[:10],
    })


# ─────────────────────────────────────────────
# RANKING
# ─────────────────────────────────────────────
@login_required
def ranking_view(request):
    from .models import Rank
    from transactions.models import Transaction
    from investments.models import Investment
    from django.db.models import Sum

    ranks = Rank.objects.filter(is_active=True).order_by('sort_order')
    user  = request.user
    total_dep = Transaction.objects.filter(user=user, type='deposit', status='completed').aggregate(t=Sum('amount'))['t'] or 0
    total_inv = Investment.objects.filter(user=user).aggregate(t=Sum('amount'))['t'] or 0
    ref_count = User.objects.filter(referred_by=user).count()

    # Determine current rank
    current_rank = None
    for rank in ranks:
        if total_dep >= rank.min_deposit and ref_count >= rank.min_referrals and total_inv >= rank.min_investment:
            current_rank = rank

    leaderboard = User.objects.filter(is_staff=False).annotate(
        total=Sum('transactions__amount', filter=DjQ(transactions__type='deposit', transactions__status='completed'))
    ).order_by('-total')[:10]

    return render(request, 'accounts/ranking.html', {
        'ranks': ranks, 'current_rank': current_rank,
        'total_dep': total_dep, 'total_inv': total_inv, 'ref_count': ref_count,
        'leaderboard': leaderboard,
    })


# ─────────────────────────────────────────────
# BALANCE TRANSFER
# ─────────────────────────────────────────────
@login_required
def transfer_view(request):
    from .models import BalanceTransfer, SiteSettings
    settings = SiteSettings.get()
    if not settings.allow_transfer:
        messages.error(request, 'Balance transfer is currently disabled.')
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('recipient','').strip()
        try:
            amount = Decimal(request.POST.get('amount','0'))
        except Exception:
            messages.error(request, 'Invalid amount.'); return redirect('transfer')

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.'); return redirect('transfer')

        # Find recipient
        from django.db.models import Q as DbQ
        recipient = User.objects.filter(DbQ(email=identifier) | DbQ(referral_code=identifier)).exclude(id=request.user.id).first()
        if not recipient:
            messages.error(request, 'Recipient not found.'); return redirect('transfer')

        fee = amount * settings.transfer_fee_pct / 100
        total_needed = amount + fee
        if request.user.wallet_balance < total_needed:
            messages.error(request, f'Insufficient balance. Need ${total_needed:.2f} (incl. fee).'); return redirect('transfer')

        request.user.wallet_balance -= total_needed
        request.user.save(update_fields=['wallet_balance'])
        recipient.wallet_balance += amount
        recipient.save(update_fields=['wallet_balance'])

        transfer = BalanceTransfer.objects.create(
            sender=request.user, recipient=recipient,
            amount=amount, fee=fee, net_amount=amount, status='completed',
        )
        from transactions.models import Transaction
        Transaction.objects.create(user=request.user, type='withdrawal', method='wallet',
            amount=total_needed, net_amount=total_needed, status='completed',
            description=f'Transfer to {recipient.email}')
        Transaction.objects.create(user=recipient, type='deposit', method='wallet',
            amount=amount, net_amount=amount, status='completed',
            description=f'Transfer from {request.user.email}')

        Notification.objects.create(user=recipient, type='deposit',
            title=f'Transfer Received — ${amount:.2f}',
            body=f'{request.user.full_name} transferred ${amount:.2f} to your wallet.')
        messages.success(request, f'Successfully transferred ${amount:.2f} to {recipient.full_name}.')
        return redirect('transactions')

    recent = BalanceTransfer.objects.filter(sender=request.user).order_by('-created_at')[:5]
    return render(request, 'accounts/transfer.html', {'settings': settings, 'recent': recent})


# ─────────────────────────────────────────────
# SUPPORT TICKETS
# ─────────────────────────────────────────────
@login_required
def tickets_view(request):
    from .models import SupportTicket
    if request.method == 'POST':
        subject  = request.POST.get('subject','').strip()
        message  = request.POST.get('message','').strip()
        priority = request.POST.get('priority','medium')
        if not subject or not message:
            messages.error(request, 'Subject and message are required.')
            return redirect('tickets')
        ticket = SupportTicket.objects.create(user=request.user, subject=subject, priority=priority)
        from .models import TicketMessage
        msg = TicketMessage.objects.create(ticket=ticket, sender=request.user, message=message)
        if 'attachment' in request.FILES:
            msg.attachment = request.FILES['attachment']; msg.save()
        Notification.objects.create(user=request.user, type='system',
            title=f'Ticket #{ticket.ticket_id} Created',
            body=f'Your support ticket "{subject}" has been submitted.')
        messages.success(request, f'Ticket #{ticket.ticket_id} created successfully.')
        return redirect('ticket_detail', pk=ticket.id)

    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/tickets.html', {'tickets': tickets})


@login_required
def ticket_detail_view(request, pk):
    from .models import SupportTicket, TicketMessage
    ticket = get_object_or_404(SupportTicket, pk=pk, user=request.user)
    if request.method == 'POST':
        message = request.POST.get('message','').strip()
        if message:
            msg = TicketMessage.objects.create(ticket=ticket, sender=request.user, message=message)
            if 'attachment' in request.FILES:
                msg.attachment = request.FILES['attachment']; msg.save()
            ticket.status = 'pending'; ticket.save(update_fields=['status'])
            messages.success(request, 'Reply sent.')
            return redirect('ticket_detail', pk=ticket.id)
    ticket_messages = ticket.messages.all()
    return render(request, 'accounts/ticket_detail.html', {'ticket': ticket, 'msgs': ticket_messages})


# ─────────────────────────────────────────────
# ACCOUNT STATEMENT
# ─────────────────────────────────────────────
@login_required
def statement_view(request):
    from transactions.models import Transaction
    from django.utils import timezone as tz
    from datetime import timedelta

    period = request.GET.get('period','monthly')
    fmt    = request.GET.get('format','html')
    today  = tz.now()

    date_ranges = {
        'daily':   today - timedelta(days=1),
        'weekly':  today - timedelta(weeks=1),
        'monthly': today - timedelta(days=30),
        'yearly':  today - timedelta(days=365),
    }
    date_from_str = request.GET.get('from','')
    date_to_str   = request.GET.get('to','')

    qs = Transaction.objects.filter(user=request.user, status='completed')
    if date_from_str and date_to_str:
        qs = qs.filter(created_at__date__gte=date_from_str, created_at__date__lte=date_to_str)
    elif period in date_ranges:
        qs = qs.filter(created_at__gte=date_ranges[period])
    qs = qs.order_by('created_at')

    from django.db.models import Sum
    summary = {
        'deposits':    qs.filter(type='deposit').aggregate(t=Sum('amount'))['t'] or 0,
        'withdrawals': qs.filter(type='withdrawal').aggregate(t=Sum('amount'))['t'] or 0,
        'roi':         qs.filter(type='roi').aggregate(t=Sum('amount'))['t'] or 0,
        'referral':    qs.filter(type='referral').aggregate(t=Sum('amount'))['t'] or 0,
        'investments': qs.filter(type='investment').aggregate(t=Sum('amount'))['t'] or 0,
    }

    if fmt == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="statement.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID','Type','Description','Amount','Fee','Date','Status'])
        for t in qs:
            writer.writerow([t.txn_id, t.type, t.description, t.amount, t.fee, t.created_at.strftime('%Y-%m-%d %H:%M'), t.status])
        return response

    return render(request, 'accounts/statement.html', {
        'transactions': qs, 'summary': summary,
        'period': period, 'date_from': date_from_str, 'date_to': date_to_str,
    })


# ─────────────────────────────────────────────
# INVESTMENT REPORT
# ─────────────────────────────────────────────
@login_required
def investment_report_view(request):
    from investments.models import Investment
    from transactions.models import Transaction
    from django.utils import timezone as tz
    from datetime import timedelta

    user = request.user
    investments = Investment.objects.filter(user=user).select_related('plan').order_by('-created_at')

    total_invested  = sum((i.amount for i in investments), Decimal('0'))
    total_profit    = sum((i.profit_earned for i in investments), Decimal('0'))
    active_count    = investments.filter(status='active').count()
    completed_count = investments.filter(status='completed').count()
    cancelled_count = investments.filter(status='cancelled').count()

    # Monthly profit breakdown (last 6 months) from ROI transactions
    monthly = []
    for i in range(5, -1, -1):
        d = tz.now() - timedelta(days=30 * i)
        amt = Transaction.objects.filter(user=user, type='roi', status='completed',
            created_at__year=d.year, created_at__month=d.month).aggregate(t=Sum('amount'))['t'] or 0
        monthly.append({'month': d.strftime('%b'), 'amount': float(amt)})

    # Per-plan breakdown
    plan_breakdown = investments.values('plan__name').annotate(
        total=Sum('amount'), profit=Sum('profit_earned'), count=Count('id')
    ).order_by('-total')

    return render(request, 'accounts/investment_report.html', {
        'investments': investments,
        'total_invested': total_invested,
        'total_profit': total_profit,
        'active_count': active_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'monthly': monthly,
        'plan_breakdown': plan_breakdown,
        'roi_pct': (total_profit / total_invested * 100) if total_invested else 0,
    })
