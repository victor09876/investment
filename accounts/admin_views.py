from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from decimal import Decimal
import django, sys, platform, os

from .models import (User, Notification, SiteSettings, RegistrationCode,
                     LoginHistory, CacheLog, SupportTicket, TicketMessage,
                     KYCField, KYCSubmission, KYCAnswer, Branding, Rank, CronJobLog,
                     InvestmentDuration, FrontPage)
from investments.models import Plan, Investment
from transactions.models import Transaction

staff_required = user_passes_test(lambda u: u.is_staff, login_url='/login/')
def staff_view(func):
    return login_required(staff_required(func))


def get_admin_stats():
    today = timezone.now().date()
    week_ago = timezone.now() - timedelta(days=7)
    return {
        'total_users':        User.objects.filter(is_staff=False).count(),
        'active_users':       User.objects.filter(is_active=True, is_staff=False).count(),
        'new_users_week':     User.objects.filter(date_joined__gte=week_ago, is_staff=False).count(),
        'total_deposited':    Transaction.objects.filter(type='deposit',status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'total_withdrawn':    Transaction.objects.filter(type='withdrawal',status='completed').aggregate(t=Sum('amount'))['t'] or 0,
        'pending_deposits':   Transaction.objects.filter(type='deposit',status='pending').count(),
        'pending_withdrawals':Transaction.objects.filter(type='withdrawal',status__in=['pending','processing']).count(),
        'active_investments': Investment.objects.filter(status='active').count(),
        'total_invested':     Investment.objects.filter(status='active').aggregate(t=Sum('amount'))['t'] or 0,
        'today_roi':          Transaction.objects.filter(type='roi',created_at__date=today).aggregate(t=Sum('amount'))['t'] or 0,
        'platform_profit':    (Transaction.objects.filter(type='deposit',status='completed').aggregate(t=Sum('amount'))['t'] or 0)
                             -(Transaction.objects.filter(type__in=['withdrawal','roi','refund'],status='completed').aggregate(t=Sum('amount'))['t'] or 0),
        'open_tickets':       SupportTicket.objects.filter(status='open').count(),
        'pending_kyc':        KYCSubmission.objects.filter(status='pending').count(),
    }


@staff_view
def admin_dashboard(request):
    stats = get_admin_stats()
    recent_txns  = Transaction.objects.select_related('user').order_by('-created_at')[:10]
    recent_users = User.objects.filter(is_staff=False).order_by('-date_joined')[:8]
    pending_txns = Transaction.objects.select_related('user').filter(status__in=['pending','processing']).order_by('-created_at')[:5]
    monthly = []
    for i in range(5,-1,-1):
        d = timezone.now() - timedelta(days=30*i)
        dep = Transaction.objects.filter(type='deposit',status='completed',created_at__year=d.year,created_at__month=d.month).aggregate(t=Sum('amount'))['t'] or 0
        wth = Transaction.objects.filter(type='withdrawal',status='completed',created_at__year=d.year,created_at__month=d.month).aggregate(t=Sum('amount'))['t'] or 0
        monthly.append({'month':d.strftime('%b'),'deposit':float(dep),'withdrawal':float(wth)})

    # Login analytics last 30 days
    since = timezone.now()-timedelta(days=30)
    by_browser = LoginHistory.objects.filter(created_at__gte=since).values('browser').annotate(count=Count('id')).order_by('-count')[:6]
    by_os      = LoginHistory.objects.filter(created_at__gte=since).values('os').annotate(count=Count('id')).order_by('-count')[:6]
    by_country = LoginHistory.objects.filter(created_at__gte=since).values('country').annotate(count=Count('id')).order_by('-count')[:8]

    pending_txns_count = (stats['pending_deposits'] or 0) + (stats['pending_withdrawals'] or 0)
    return render(request,'custom_admin/dashboard.html',{
        'stats':stats,'recent_txns':recent_txns,'recent_users':recent_users,
        'monthly':monthly,'pending_txns':pending_txns,'pending_txns_count':pending_txns_count,
        'by_browser':list(by_browser),'by_os':list(by_os),'by_country':list(by_country),
    })


@staff_view
def admin_users(request):
    qs = User.objects.filter(is_staff=False).annotate(inv_count=Count('investments'),txn_count=Count('transactions'))
    q,status,kyc = request.GET.get('q',''),request.GET.get('status',''),request.GET.get('kyc','')
    if q:      qs = qs.filter(Q(email__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q)|Q(phone__icontains=q))
    if status == 'active':   qs = qs.filter(is_active=True)
    if status == 'inactive': qs = qs.filter(is_active=False)
    if kyc:    qs = qs.filter(kyc_status=kyc)
    return render(request,'custom_admin/users.html',{'users':qs.order_by('-date_joined'),'q':q,'status':status,'kyc':kyc})


@staff_view
def admin_user_detail(request, pk):
    user = get_object_or_404(User, pk=pk, is_staff=False)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_active':
            user.is_active = not user.is_active; user.save(update_fields=['is_active'])
            messages.success(request, f'User {"activated" if user.is_active else "deactivated"}.')
        elif action == 'update_kyc':
            user.kyc_status = request.POST.get('kyc_status','not_submitted')
            user.is_kyc_verified = (user.kyc_status == 'verified')
            user.save(update_fields=['kyc_status','is_kyc_verified'])
            messages.success(request,'KYC status updated.')
        elif action == 'adjust_balance':
            try:
                amount = Decimal(request.POST.get('amount','0'))
                bal_type = request.POST.get('bal_type','wallet')
                note = request.POST.get('note','Admin adjustment')
                if bal_type == 'wallet': user.wallet_balance += amount
                else: user.profit_balance += amount
                user.save(update_fields=[f'{bal_type}_balance'])
                Transaction.objects.create(user=user,type='deposit' if amount>0 else 'withdrawal',method='wallet',amount=abs(amount),net_amount=abs(amount),status='completed',description=f'Admin: {note}')
                Notification.objects.create(user=user,type='system',title='Balance Adjusted',body=f'Your balance was adjusted by ${amount:+.2f}.')
                messages.success(request,f'Balance adjusted by ${amount:+.2f}.')
            except Exception as e: messages.error(request,f'Error: {e}')
        elif action == 'reset_password':
            new_pw = request.POST.get('new_password','')
            if len(new_pw) >= 8:
                user.set_password(new_pw); user.save()
                messages.success(request,'Password reset.')
            else: messages.error(request,'Min 8 characters.')
        elif action == 'send_notification':
            title = request.POST.get('notif_title','')
            body  = request.POST.get('notif_body','')
            if title and body:
                Notification.objects.create(user=user,type='system',title=title,body=body)
                messages.success(request,'Notification sent.')
        elif action == 'login_as':
            from django.contrib.auth import login as auth_login
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)
            messages.info(request,f'Logged in as {user.email}')
            return redirect('dashboard')
        elif action == 'review_kyc':
            sub = KYCSubmission.objects.filter(user=user).first()
            if sub:
                decision = request.POST.get('kyc_decision','pending')
                sub.status = decision
                sub.admin_note = request.POST.get('kyc_note','')
                sub.reviewed_at = timezone.now()
                sub.reviewed_by = request.user
                sub.save()
                user.is_kyc_verified = (decision == 'approved')
                user.kyc_status = {'approved':'verified','rejected':'rejected'}.get(decision, 'submitted')
                user.save(update_fields=['is_kyc_verified','kyc_status'])
                Notification.objects.create(user=user, type='system',
                    title=f'KYC {decision.title()}',
                    body=f'Your KYC verification has been {decision}.' + (f' Note: {sub.admin_note}' if sub.admin_note else ''))
                messages.success(request, f'KYC {decision}.')
        return redirect('admin_user_detail',pk=pk)

    investments  = Investment.objects.filter(user=user).select_related('plan').order_by('-created_at')
    transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:30]
    login_hist   = LoginHistory.objects.filter(user=user).order_by('-created_at')[:20]
    tickets      = SupportTicket.objects.filter(user=user).order_by('-created_at')
    kyc_sub      = KYCSubmission.objects.filter(user=user).first()
    kyc_answers  = KYCAnswer.objects.filter(submission=kyc_sub).select_related('field').order_by('field__sort_order') if kyc_sub else []
    notifs       = Notification.objects.filter(user=user).order_by('-created_at')[:10]
    return render(request,'custom_admin/user_detail.html',{
        'u':user,'investments':investments,'transactions':transactions,
        'login_hist':login_hist,'tickets':tickets,'kyc_sub':kyc_sub,'kyc_answers':kyc_answers,'notifs':notifs,
    })


@staff_view
def admin_transactions(request):
    qs = Transaction.objects.select_related('user').order_by('-created_at')
    txn_type,txn_status,q = request.GET.get('type',''),request.GET.get('status',''),request.GET.get('q','')
    if txn_type:   qs = qs.filter(type=txn_type)
    if txn_status: qs = qs.filter(status=txn_status)
    if q: qs = qs.filter(Q(txn_id__icontains=q)|Q(user__email__icontains=q)|Q(description__icontains=q))
    if request.method == 'POST':
        action  = request.POST.get('action')
        txn_ids = request.POST.getlist('txn_ids')
        count = 0
        for tid in txn_ids:
            try:
                txn = Transaction.objects.get(id=tid)
                if action == 'approve':
                    if txn.type == 'deposit' and txn.status == 'pending':
                        txn.status='completed'; txn.processed_at=timezone.now(); txn.save()
                        txn.user.wallet_balance += txn.net_amount
                        txn.user.save(update_fields=['wallet_balance'])
                        Notification.objects.create(user=txn.user,type='deposit',title=f'Deposit Confirmed — ${txn.amount:,.2f}',body=f'Your ${txn.amount:,.2f} deposit has been credited.')
                    elif txn.type == 'withdrawal' and txn.status in ('pending','processing'):
                        txn.status='completed'; txn.processed_at=timezone.now(); txn.save()
                        Notification.objects.create(user=txn.user,type='withdrawal',title=f'Withdrawal Paid — ${txn.amount:,.2f}',body=f'Your withdrawal of ${txn.amount:,.2f} has been processed.')
                    count += 1
                elif action == 'reject':
                    if txn.type=='withdrawal' and txn.status in ('pending','processing'):
                        txn.user.wallet_balance += txn.amount
                        txn.user.save(update_fields=['wallet_balance'])
                    txn.status='failed'; txn.save()
                    Notification.objects.create(user=txn.user,type='system',title='Transaction Rejected',body=f'Your {txn.type} of ${txn.amount:,.2f} was rejected.')
                    count += 1
            except Transaction.DoesNotExist: pass
        messages.success(request,f'{count} transaction(s) updated.')
        return redirect('admin_transactions')
    pending_dep = Transaction.objects.filter(type='deposit',status='pending').count()
    pending_wth = Transaction.objects.filter(type='withdrawal',status__in=['pending','processing']).count()
    return render(request,'custom_admin/transactions.html',{
        'transactions':qs,'txn_type':txn_type,'txn_status':txn_status,'q':q,
        'pending_dep':pending_dep,'pending_wth':pending_wth,
    })


@staff_view
def admin_investments(request):
    qs = Investment.objects.select_related('user','plan').order_by('-created_at')
    status,q = request.GET.get('status',''),request.GET.get('q','')
    if status: qs = qs.filter(status=status)
    if q: qs = qs.filter(Q(user__email__icontains=q)|Q(plan__name__icontains=q))
    stats = {
        'active_total':    Investment.objects.filter(status='active').aggregate(t=Sum('amount'))['t'] or 0,
        'active_count':    Investment.objects.filter(status='active').count(),
        'completed_profit':Investment.objects.filter(status='completed').aggregate(t=Sum('profit_earned'))['t'] or 0,
    }
    return render(request,'custom_admin/investments.html',{'investments':qs,'status':status,'q':q,'stats':stats})


@staff_view
def admin_plans(request):
    plans = Plan.objects.all().order_by('sort_order')
    durations = InvestmentDuration.objects.filter(is_active=True)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            try:
                Plan.objects.create(
                    name=request.POST['name'], slug=request.POST['slug'],
                    icon=request.POST.get('icon','chart-line'),
                    description=request.POST.get('description',''),
                    daily_roi=Decimal(request.POST['daily_roi']),
                    duration_days=int(request.POST['duration_days']),
                    min_amount=Decimal(request.POST['min_amount']),
                    max_amount=Decimal(request.POST['max_amount']) if request.POST.get('max_amount') else None,
                    referral_bonus_pct=Decimal(request.POST.get('referral_bonus_pct','5')),
                    is_featured=request.POST.get('is_featured')=='on',
                    sort_order=int(request.POST.get('sort_order',0)))
                messages.success(request,'Plan created.')
            except Exception as e: messages.error(request,f'Error: {e}')
        elif action == 'toggle':
            plan=get_object_or_404(Plan,id=request.POST.get('plan_id'))
            plan.is_active=not plan.is_active; plan.save()
            messages.success(request,'Plan updated.')
        elif action == 'delete':
            plan=get_object_or_404(Plan,id=request.POST.get('plan_id'))
            if not Investment.objects.filter(plan=plan,status='active').exists():
                plan.delete(); messages.success(request,'Plan deleted.')
            else: messages.error(request,'Cannot delete plan with active investments.')
        return redirect('admin_plans')
    return render(request,'custom_admin/plans.html',{'plans':plans,'durations':durations})


@staff_view
def admin_settings(request):
    site = SiteSettings.get()
    if request.method == 'POST':
        fields = [
            'site_name','maintenance_mode','require_reg_code','min_deposit','min_withdrawal',
            'withdrawal_fee_pct','cancellation_fee_pct','welcome_bonus',
            'bitcoin_address','usdt_trc20_address','usdt_erc20_address','ethereum_address',
            'bank_name','bank_account_name','bank_account_number','bank_routing','bank_swift',
            'allow_registration','allow_google_login','allow_apple_login','allow_metamask_login',
            'allow_transfer','allow_ranking','require_kyc_deposit','require_kyc_withdraw',
            'require_email_verify','allow_withdraw_holiday','secure_password',
            'currency','currency_symbol','timezone','records_per_page',
            'transfer_fee_pct','custom_css','app_version','maintenance_message',
            'allow_investment_cancellation','deposit_timeout_minutes','cron_interval_minutes',
        ]
        bool_fields = ['maintenance_mode','require_reg_code','allow_registration','allow_google_login',
                       'allow_apple_login','allow_metamask_login','allow_transfer','allow_ranking',
                       'require_kyc_deposit','require_kyc_withdraw','require_email_verify',
                       'allow_withdraw_holiday','secure_password','allow_investment_cancellation']
        decimal_fields = ['min_deposit','min_withdrawal','withdrawal_fee_pct','cancellation_fee_pct',
                          'welcome_bonus','transfer_fee_pct']
        int_fields = ['records_per_page','deposit_timeout_minutes','cron_interval_minutes']
        for f in fields:
            if f in bool_fields:
                setattr(site, f, request.POST.get(f) == 'on')
            elif f in decimal_fields:
                try: setattr(site, f, Decimal(request.POST.get(f,'0')))
                except: pass
            elif f in int_fields:
                try: setattr(site, f, int(request.POST.get(f, getattr(site, f, 5))))
                except: pass
            else:
                setattr(site, f, request.POST.get(f,''))
        if 'maintenance_image' in request.FILES:
            site.maintenance_image = request.FILES['maintenance_image']
        site.save()
        messages.success(request,'Settings saved.')
        return redirect('admin_settings')
    return render(request,'custom_admin/settings.html',{'site':site})


@staff_view
def admin_branding(request):
    branding = Branding.get()
    if request.method == 'POST':
        img_fields = ['site_logo','dark_logo','light_logo','mobile_logo','favicon','login_logo','email_logo','footer_logo']
        for f in img_fields:
            if f in request.FILES:
                setattr(branding, f, request.FILES[f])
        branding.save()
        messages.success(request,'Branding updated successfully.')
        return redirect('admin_branding')
    logo_items_primary = [
        {'name':'site_logo','label':'Site Logo','hint':'Main logo — sidebar & header','current':branding.site_logo or None},
        {'name':'dark_logo','label':'Dark Mode Logo','hint':'For dark backgrounds','current':branding.dark_logo or None},
        {'name':'light_logo','label':'Light Mode Logo','hint':'For light backgrounds','current':branding.light_logo or None},
        {'name':'mobile_logo','label':'Mobile Logo','hint':'Compact logo for mobile','current':branding.mobile_logo or None},
    ]
    logo_items_secondary = [
        {'name':'favicon','label':'Favicon','hint':'Browser tab icon (32×32px)','current':branding.favicon or None},
        {'name':'login_logo','label':'Login Page Logo','hint':'Shown on auth pages','current':branding.login_logo or None},
        {'name':'email_logo','label':'Email Logo','hint':'Used in email templates','current':branding.email_logo or None},
        {'name':'footer_logo','label':'Footer Logo','hint':'Used in website footer','current':branding.footer_logo or None},
    ]
    current_logos = [
        ('site_logo','Site Logo', branding.site_logo if branding.site_logo else None),
        ('favicon','Favicon', branding.favicon if branding.favicon else None),
        ('login_logo','Login Logo', branding.login_logo if branding.login_logo else None),
        ('footer_logo','Footer Logo', branding.footer_logo if branding.footer_logo else None),
    ]
    return render(request,'custom_admin/branding.html',{
        'branding':branding,'active':'branding',
        'logo_items_primary':logo_items_primary,
        'logo_items_secondary':logo_items_secondary,
        'current_logos':current_logos,
    })


@staff_view
def admin_reg_codes(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'generate':
            count = int(request.POST.get('count',1))
            label = request.POST.get('label','')
            max_uses = int(request.POST.get('max_uses',1))
            expires_str = request.POST.get('expires_at','')
            expires_at = None
            if expires_str:
                try:
                    from django.utils.dateparse import parse_datetime
                    expires_at = timezone.make_aware(timezone.datetime.fromisoformat(expires_str))
                except: pass
            for _ in range(min(count,50)):
                RegistrationCode.objects.create(label=label,max_uses=max_uses,expires_at=expires_at)
            messages.success(request,f'{count} code(s) generated.')
        elif action == 'toggle':
            code=get_object_or_404(RegistrationCode,id=request.POST.get('code_id'))
            code.is_active=not code.is_active; code.save()
            messages.success(request,'Code toggled.')
        elif action == 'delete':
            RegistrationCode.objects.filter(id=request.POST.get('code_id')).delete()
            messages.success(request,'Code deleted.')
        return redirect('admin_reg_codes')
    codes = RegistrationCode.objects.all().order_by('-created_at')
    site  = SiteSettings.get()
    return render(request,'custom_admin/reg_codes.html',{'codes':codes,'site':site})


@staff_view
def admin_kyc(request):
    fields = KYCField.objects.all().order_by('sort_order')
    submissions = KYCSubmission.objects.select_related('user').filter(status='pending').order_by('-submitted_at')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_field':
            KYCField.objects.create(
                label=request.POST['label'], field_type=request.POST['field_type'],
                placeholder=request.POST.get('placeholder',''), options=request.POST.get('options',''),
                is_required=request.POST.get('is_required')=='on',
                sort_order=int(request.POST.get('sort_order',0)))
            messages.success(request,'KYC field created.')
        elif action == 'delete_field':
            KYCField.objects.filter(id=request.POST.get('field_id')).delete()
            messages.success(request,'Field deleted.')
        elif action == 'toggle_field':
            f=get_object_or_404(KYCField,id=request.POST.get('field_id'))
            f.is_active=not f.is_active; f.save()
        elif action == 'review':
            sub = get_object_or_404(KYCSubmission, id=request.POST.get('sub_id'))
            new_status = request.POST.get('status','pending')
            sub.status = new_status; sub.admin_note = request.POST.get('note','')
            sub.reviewed_at = timezone.now(); sub.reviewed_by = request.user; sub.save()
            sub.user.is_kyc_verified = (new_status == 'approved')
            sub.user.kyc_status = {'approved':'verified','rejected':'rejected','pending':'submitted'}.get(new_status, 'submitted')
            sub.user.save(update_fields=['is_kyc_verified','kyc_status'])
            Notification.objects.create(user=sub.user, type='system',
                title=f'KYC {new_status.title()}',
                body=f'Your KYC verification has been {new_status}.' + (f' Note: {sub.admin_note}' if sub.admin_note else ''))
            messages.success(request,f'KYC {new_status}.')
        return redirect('admin_kyc')
    all_subs = KYCSubmission.objects.select_related('user').order_by('-submitted_at')
    return render(request,'custom_admin/kyc.html',{'fields':fields,'submissions':submissions,'all_subs':all_subs})


@staff_view
def admin_ranks(request):
    ranks = Rank.objects.all().order_by('sort_order')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            Rank.objects.create(
                name=request.POST['name'], color=request.POST.get('color','#C9A84C'),
                min_deposit=Decimal(request.POST.get('min_deposit','0')),
                min_referrals=int(request.POST.get('min_referrals',0)),
                min_investment=Decimal(request.POST.get('min_investment','0')),
                weekly_reward=Decimal(request.POST.get('weekly_reward','0')),
                rank_bonus_pct=Decimal(request.POST.get('rank_bonus_pct','0')),
                special_roi_pct=Decimal(request.POST.get('special_roi_pct','0')),
                description=request.POST.get('description',''),
                sort_order=int(request.POST.get('sort_order',0)),
            )
            messages.success(request,'Rank created.')
        elif action == 'delete':
            Rank.objects.filter(id=request.POST.get('rank_id')).delete()
            messages.success(request,'Rank deleted.')
        return redirect('admin_ranks')
    return render(request,'custom_admin/ranks.html',{'ranks':ranks})


@staff_view
def admin_tickets(request):
    qs = SupportTicket.objects.select_related('user').order_by('-created_at')
    status = request.GET.get('status','')
    if status: qs = qs.filter(status=status)
    return render(request,'custom_admin/tickets.html',{'tickets':qs,'status':status})


@staff_view
def admin_ticket_detail(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reply':
            msg_text = request.POST.get('message','').strip()
            if msg_text:
                msg = TicketMessage.objects.create(ticket=ticket, sender=request.user, message=msg_text, is_admin=True)
                if 'attachment' in request.FILES:
                    msg.attachment = request.FILES['attachment']; msg.save()
                ticket.status = 'pending'; ticket.save(update_fields=['status'])
                Notification.objects.create(user=ticket.user, type='system',
                    title=f'Support Reply — #{ticket.ticket_id}', body='Admin replied to your support ticket.')
                messages.success(request,'Reply sent.')
        elif action == 'status':
            ticket.status = request.POST.get('new_status','open')
            if ticket.status == 'closed': ticket.closed_at = timezone.now()
            ticket.save(); messages.success(request,'Status updated.')
        return redirect('admin_ticket_detail', pk=pk)
    msgs = ticket.messages.all()
    return render(request,'custom_admin/ticket_detail.html',{'ticket':ticket,'msgs':msgs})


@staff_view
def admin_notifications_send(request):
    if request.method == 'POST':
        title   = request.POST.get('title','')
        body    = request.POST.get('body','')
        target  = request.POST.get('target','all')
        user_ids= request.POST.getlist('user_ids')
        ntype   = request.POST.get('ntype','system')
        if not title or not body:
            messages.error(request,'Title and message are required.'); return redirect('admin_notifications')
        if target == 'all':
            users = User.objects.filter(is_staff=False, is_active=True)
        else:
            users = User.objects.filter(id__in=user_ids)
        created = 0
        for user in users:
            Notification.objects.create(user=user, type=ntype, title=title, body=body)
            created += 1
        messages.success(request,f'Notification sent to {created} user(s).')
    return redirect('admin_notifications_list')


@staff_view
def admin_notifications_list(request):
    notifs = Notification.objects.select_related('user').order_by('-created_at')[:200]
    users  = User.objects.filter(is_staff=False,is_active=True).order_by('first_name')
    stats = {
        'total':  Notification.objects.count(),
        'unread': Notification.objects.filter(is_read=False).count(),
        'today':  Notification.objects.filter(created_at__date=timezone.now().date()).count(),
    }
    return render(request,'custom_admin/notifications.html',{'notifs':notifs,'users':users,'stats':stats})


@staff_view
def admin_server_info(request):
    try:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_pct = psutil.cpu_percent(interval=0.5)
        boot = psutil.boot_time()
        uptime = timezone.now().timestamp() - boot
        uptime_str = f"{int(uptime//3600)}h {int((uptime%3600)//60)}m"
        mem_used_pct = mem.percent
        disk_used_pct = disk.percent
    except ImportError:
        mem_used_pct = disk_used_pct = cpu_pct = 0
        uptime_str = 'N/A'
        mem = disk = None

    import django as dj
    db_engine = 'SQLite'
    try:
        from django.db import connection
        db_ver = connection.Database.sqlite_version_info
        db_ver_str = '.'.join(map(str, db_ver))
    except Exception:
        db_ver_str = 'Unknown'

    info = {
        'Django Version':    dj.get_version(),
        'Python Version':    sys.version.split()[0],
        'Database':          f'SQLite {db_ver_str}',
        'OS':                f'{platform.system()} {platform.release()}',
        'Server IP':         request.META.get('SERVER_ADDR','127.0.0.1'),
        'Protocol':          'HTTPS' if request.is_secure() else 'HTTP',
        'HTTP Host':         request.get_host(),
        'Server Port':       request.META.get('SERVER_PORT','8000'),
    }
    perf = {'cpu':cpu_pct,'memory':mem_used_pct,'disk':disk_used_pct,'uptime':uptime_str}
    if mem:
        perf['mem_total'] = f"{mem.total//(1024**3):.1f} GB"
        perf['mem_used']  = f"{mem.used//(1024**3):.1f} GB"
    if disk:
        perf['disk_total'] = f"{disk.total//(1024**3):.1f} GB"
        perf['disk_used']  = f"{disk.used//(1024**3):.1f} GB"
    return render(request,'custom_admin/server_info.html',{'info':info,'perf':perf})


@staff_view
def admin_app_info(request):
    site = SiteSettings.get()
    info = {
        'application_name': site.site_name or 'InvestPro',
        'version':          site.app_version or '1.0.0',
        'environment':      'Production' if not site.maintenance_mode else 'Maintenance',
        'timezone':         site.timezone or 'UTC',
        'currency':         site.currency or 'USD',
        'currency_symbol':  site.currency_symbol or '$',
        'language':         site.language or 'English',
        'maintenance':      'ON' if site.maintenance_mode else 'OFF',
        'registration':     'ON' if site.allow_registration else 'OFF',
        'last_deployment':  site.last_deployment.strftime('%b %d, %Y %H:%M') if site.last_deployment else 'N/A',
    }
    return render(request,'custom_admin/app_info.html',{'info':info})


@staff_view
def admin_cache(request):
    if request.method == 'POST':
        from django.core.cache import cache
        cache.clear()
        import tempfile, glob
        for tmp in glob.glob(os.path.join(tempfile.gettempdir(),'django_*')):
            try: os.remove(tmp)
            except: pass
        CacheLog.objects.create(cleared_by=request.user, details='Full cache clear: app,session,temp')
        messages.success(request,'All cache cleared successfully.')
        return redirect('admin_cache')
    last_clear = CacheLog.objects.first()
    return render(request,'custom_admin/cache.html',{'last_clear':last_clear})


@staff_view
def admin_cron(request):
    crons = CronJobLog.objects.all().order_by('name')
    site = SiteSettings.get()
    return render(request,'custom_admin/cron.html',{'crons':crons,'site':site})


@staff_view
def admin_login_analytics(request):
    since = timezone.now()-timedelta(days=30)
    by_browser = list(LoginHistory.objects.filter(created_at__gte=since).values('browser').annotate(count=Count('id')).order_by('-count')[:8])
    by_os      = list(LoginHistory.objects.filter(created_at__gte=since).values('os').annotate(count=Count('id')).order_by('-count')[:8])
    by_country = list(LoginHistory.objects.filter(created_at__gte=since).values('country').annotate(count=Count('id')).order_by('-count')[:10])
    total = LoginHistory.objects.filter(created_at__gte=since).count() or 1
    for item in by_country: item['pct'] = round(item['count']/total*100,1)
    return render(request,'custom_admin/login_analytics.html',{'by_browser':by_browser,'by_os':by_os,'by_country':by_country,'total':total})


@staff_view
def admin_credit_roi(request):
    if request.method == 'POST':
        from .cron_tasks import run_all_cron_tasks
        result = run_all_cron_tasks(trigger='manual')
        messages.success(request, f"ROI credited to {result['roi_count']} investments. {result['completed_count']} completed. {result['expired_count']} expired deposits cleaned up.")
    return redirect('admin_dashboard')
