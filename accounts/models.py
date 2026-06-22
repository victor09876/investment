from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid, random, string

def gen_referral():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def gen_reg_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user
    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)

class SiteSettings(models.Model):
    """Singleton site-wide settings"""
    require_reg_code    = models.BooleanField(default=False, verbose_name='Require Registration Code')
    site_name           = models.CharField(max_length=100, default='InvestPro')
    maintenance_mode    = models.BooleanField(default=False)
    min_deposit         = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    min_withdrawal      = models.DecimalField(max_digits=10, decimal_places=2, default=20)
    withdrawal_fee_pct  = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cancellation_fee_pct= models.DecimalField(max_digits=5, decimal_places=2, default=5)
    welcome_bonus       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bitcoin_address     = models.CharField(max_length=200, blank=True)
    usdt_trc20_address  = models.CharField(max_length=200, blank=True)
    usdt_erc20_address  = models.CharField(max_length=200, blank=True)
    ethereum_address    = models.CharField(max_length=200, blank=True)
    bank_name           = models.CharField(max_length=100, blank=True)
    bank_account_name   = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_routing        = models.CharField(max_length=50, blank=True)
    bank_swift          = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Site Settings'

    def __str__(self): return 'Site Settings'

    # Feature toggles added in v2
    allow_registration   = models.BooleanField(default=True)
    allow_google_login   = models.BooleanField(default=False)
    allow_apple_login    = models.BooleanField(default=False)
    allow_metamask_login = models.BooleanField(default=False)
    allow_transfer       = models.BooleanField(default=True)
    allow_ranking        = models.BooleanField(default=True)
    require_kyc_deposit  = models.BooleanField(default=False)
    require_kyc_withdraw = models.BooleanField(default=False)
    require_email_verify = models.BooleanField(default=False)
    allow_withdraw_holiday = models.BooleanField(default=True)
    force_ssl            = models.BooleanField(default=False)
    secure_password      = models.BooleanField(default=True)
    language             = models.CharField(max_length=10, default='en')
    currency             = models.CharField(max_length=10, default='USD')
    currency_symbol      = models.CharField(max_length=5, default='$')
    timezone             = models.CharField(max_length=60, default='UTC')
    records_per_page     = models.PositiveIntegerField(default=20)
    transfer_fee_pct     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    maintenance_image    = models.ImageField(upload_to='maintenance/', null=True, blank=True)
    maintenance_message  = models.TextField(default='We are performing scheduled maintenance. We will be back shortly.')
    custom_css           = models.TextField(blank=True)
    last_deployment      = models.DateTimeField(null=True, blank=True)
    app_version          = models.CharField(max_length=20, default='1.0.0')
    allow_investment_cancellation = models.BooleanField(default=True)
    deposit_timeout_minutes        = models.PositiveIntegerField(default=30)
    cron_interval_minutes          = models.PositiveIntegerField(default=5)
    cron_last_tick                 = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RegistrationCode(models.Model):
    code        = models.CharField(max_length=20, unique=True, default=gen_reg_code)
    label       = models.CharField(max_length=100, blank=True)
    is_active   = models.BooleanField(default=True)
    max_uses    = models.PositiveIntegerField(default=1, help_text='0 = unlimited')
    times_used  = models.PositiveIntegerField(default=0, editable=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField(null=True, blank=True)

    def __str__(self): return f'{self.code} ({self.label or "no label"})'

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active: return False
        if self.max_uses > 0 and self.times_used >= self.max_uses: return False
        if self.expires_at and self.expires_at < timezone.now(): return False
        return True

    def use(self):
        self.times_used += 1
        self.save(update_fields=['times_used'])


class User(AbstractBaseUser, PermissionsMixin):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email          = models.EmailField(unique=True)
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    phone          = models.CharField(max_length=30, blank=True)
    country        = models.CharField(max_length=100, blank=True)
    state          = models.CharField(max_length=100, blank=True)
    dial_code      = models.CharField(max_length=10, blank=True)
    address        = models.TextField(blank=True)
    date_of_birth  = models.DateField(null=True, blank=True)
    gender         = models.CharField(max_length=20, blank=True)
    avatar         = models.ImageField(upload_to='avatars/', null=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    profit_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_active      = models.BooleanField(default=True)
    is_staff       = models.BooleanField(default=False)
    is_kyc_verified= models.BooleanField(default=False)
    kyc_status     = models.CharField(max_length=20, default='not_submitted',
        choices=[('not_submitted','Not Submitted'),('pending','Pending'),('submitted','Submitted'),('verified','Verified'),('rejected','Rejected')])
    referral_code  = models.CharField(max_length=20, unique=True, default=gen_referral)
    referred_by    = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
    withdrawal_pin = models.CharField(max_length=128, blank=True)
    date_joined    = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    objects = UserManager()

    @property
    def full_name(self): return f'{self.first_name} {self.last_name}'
    @property
    def initials(self): return f'{self.first_name[:1]}{self.last_name[:1]}'.upper()
    @property
    def total_balance(self): return self.wallet_balance + self.profit_balance

    def set_withdrawal_pin(self, pin):
        from django.contrib.auth.hashers import make_password
        self.withdrawal_pin = make_password(pin)

    def check_withdrawal_pin(self, pin):
        from django.contrib.auth.hashers import check_password
        return check_password(pin, self.withdrawal_pin)

    def __str__(self): return self.email


class Notification(models.Model):
    TYPES = [('roi','ROI'),('deposit','Deposit'),('withdrawal','Withdrawal'),
             ('investment','Investment'),('referral','Referral'),('security','Security'),
             ('promo','Promo'),('system','System')]
    TYPE_ICONS = {'roi':'💰','deposit':'💳','withdrawal':'💸','investment':'📊',
                  'referral':'👥','security':'🔐','promo':'🎁','system':'🔔'}
    TYPE_COLORS = {'roi':'green','deposit':'green','withdrawal':'red','investment':'blue',
                   'referral':'gold','security':'red','promo':'gold','system':'blue'}

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=20, choices=TYPES, default='system')
    title      = models.CharField(max_length=255)
    body       = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    @property
    def icon(self): return self.TYPE_ICONS.get(self.type, '🔔')
    @property
    def color(self): return self.TYPE_COLORS.get(self.type, 'blue')


# ─────────────────────────────────────────────
# BRANDING
# ─────────────────────────────────────────────
class Branding(models.Model):
    site_logo       = models.ImageField(upload_to='branding/', null=True, blank=True)
    dark_logo       = models.ImageField(upload_to='branding/', null=True, blank=True)
    light_logo      = models.ImageField(upload_to='branding/', null=True, blank=True)
    mobile_logo     = models.ImageField(upload_to='branding/', null=True, blank=True)
    favicon         = models.ImageField(upload_to='branding/', null=True, blank=True)
    login_logo      = models.ImageField(upload_to='branding/', null=True, blank=True)
    email_logo      = models.ImageField(upload_to='branding/', null=True, blank=True)
    footer_logo     = models.ImageField(upload_to='branding/', null=True, blank=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta: verbose_name = 'Branding'

    def __str__(self): return 'Branding Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ─────────────────────────────────────────────
# LOGIN HISTORY
# ─────────────────────────────────────────────
class LoginHistory(models.Model):
    STATUS = [('success','Success'),('failed','Failed')]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser    = models.CharField(max_length=100, blank=True)
    browser_ver= models.CharField(max_length=50, blank=True)
    os         = models.CharField(max_length=100, blank=True)
    os_ver     = models.CharField(max_length=50, blank=True)
    device     = models.CharField(max_length=100, blank=True)
    device_type= models.CharField(max_length=50, blank=True)  # mobile/tablet/pc
    country    = models.CharField(max_length=100, blank=True)
    country_code=models.CharField(max_length=5, blank=True)
    city       = models.CharField(max_length=100, blank=True)
    status     = models.CharField(max_length=20, choices=STATUS, default='success')
    is_new_device = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def __str__(self): return f'{self.user.email} — {self.ip_address} — {self.created_at:%Y-%m-%d %H:%M}'


# ─────────────────────────────────────────────
# CRON JOB LOG
# ─────────────────────────────────────────────
class CronJobLog(models.Model):
    STATUS = [('success','Success'),('failed','Failed'),('running','Running')]
    name          = models.CharField(max_length=100)
    slug          = models.SlugField(max_length=100)
    status        = models.CharField(max_length=20, choices=STATUS, default='success')
    last_run      = models.DateTimeField(null=True, blank=True)
    next_run      = models.DateTimeField(null=True, blank=True)
    duration_secs = models.FloatField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    last_error    = models.TextField(blank=True)
    last_output   = models.TextField(blank=True)

    def __str__(self): return self.name


# ─────────────────────────────────────────────
# CACHE LOG
# ─────────────────────────────────────────────
class CacheLog(models.Model):
    cleared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    cleared_at = models.DateTimeField(auto_now_add=True)
    details    = models.TextField(blank=True)

    class Meta: ordering = ['-cleared_at']


# ─────────────────────────────────────────────
# SUPPORT TICKET
# ─────────────────────────────────────────────
class SupportTicket(models.Model):
    PRIORITY = [('low','Low'),('medium','Medium'),('high','High'),('urgent','Urgent')]
    STATUS   = [('open','Open'),('pending','Pending'),('resolved','Resolved'),('closed','Closed')]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_id  = models.CharField(max_length=20, unique=True, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject    = models.CharField(max_length=255)
    priority   = models.CharField(max_length=20, choices=PRIORITY, default='medium')
    status     = models.CharField(max_length=20, choices=STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at  = models.DateTimeField(null=True, blank=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = 'TKT' + ''.join(random.choices(string.digits, k=7))
        super().save(*args, **kwargs)

    def __str__(self): return f'#{self.ticket_id} — {self.subject}'


class TicketMessage(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket     = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE)
    message    = models.TextField()
    attachment = models.FileField(upload_to='tickets/', null=True, blank=True)
    is_admin   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['created_at']


# ─────────────────────────────────────────────
# KYC BUILDER
# ─────────────────────────────────────────────
class KYCField(models.Model):
    FIELD_TYPES = [
        ('text','Text'),('number','Number'),('email','Email'),
        ('select','Select / Dropdown'),('date','Date'),
        ('file','File Upload'),('image','Image Upload'),('textarea','Text Area'),
    ]
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label       = models.CharField(max_length=200)
    field_type  = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    placeholder = models.CharField(max_length=200, blank=True)
    options     = models.TextField(blank=True, help_text='Comma-separated options for select fields')
    is_required = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)

    class Meta: ordering = ['sort_order','label']

    def __str__(self): return self.label

    def get_options_list(self):
        return [o.strip() for o in self.options.split(',') if o.strip()]


class KYCSubmission(models.Model):
    STATUS = [('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc_submission')
    status     = models.CharField(max_length=20, choices=STATUS, default='pending')
    admin_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    reviewed_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_reviews')

    def __str__(self): return f'{self.user.email} — {self.status}'


class KYCAnswer(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(KYCSubmission, on_delete=models.CASCADE, related_name='answers')
    field      = models.ForeignKey(KYCField, on_delete=models.CASCADE)
    value      = models.TextField(blank=True)
    file_value = models.FileField(upload_to='kyc/', null=True, blank=True)

    def __str__(self): return f'{self.field.label}: {self.value[:40]}'


# ─────────────────────────────────────────────
# RANKING SYSTEM
# ─────────────────────────────────────────────
class Rank(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=100)
    icon            = models.CharField(max_length=10, default='star', help_text='Icon name (FA class)')
    color           = models.CharField(max_length=20, default='#C9A84C')
    min_deposit     = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    min_referrals   = models.PositiveIntegerField(default=0)
    min_investment  = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    weekly_reward   = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    rank_bonus_pct  = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    special_roi_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    description     = models.TextField(blank=True)
    sort_order      = models.PositiveIntegerField(default=0)
    is_active       = models.BooleanField(default=True)

    class Meta: ordering = ['sort_order']

    def __str__(self): return self.name


# ─────────────────────────────────────────────
# BALANCE TRANSFER
# ─────────────────────────────────────────────
class BalanceTransfer(models.Model):
    STATUS = [('completed','Completed'),('failed','Failed'),('pending','Pending')]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers')
    recipient  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transfers')
    amount     = models.DecimalField(max_digits=18, decimal_places=2)
    fee        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status     = models.CharField(max_length=20, choices=STATUS, default='completed')
    note       = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def __str__(self): return f'{self.sender.email} → {self.recipient.email} ${self.amount}'


# ─────────────────────────────────────────────
# INVESTMENT DURATION
# ─────────────────────────────────────────────
class InvestmentDuration(models.Model):
    UNIT = [('hours','Hours'),('days','Days'),('weeks','Weeks'),('months','Months')]
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label     = models.CharField(max_length=50, help_text='e.g. "24 Hours", "7 Days"')
    value     = models.PositiveIntegerField(help_text='Numeric value')
    unit      = models.CharField(max_length=20, choices=UNIT, default='days')
    days      = models.PositiveIntegerField(help_text='Total equivalent days', default=1)
    is_active = models.BooleanField(default=True)
    sort_order= models.PositiveIntegerField(default=0)

    class Meta: ordering = ['days','sort_order']

    def __str__(self): return self.label


# ─────────────────────────────────────────────
# FRONTEND PAGES
# ─────────────────────────────────────────────
class FrontPage(models.Model):
    SLUGS = [
        ('home','Home'),('about','About Us'),('contact','Contact'),
        ('privacy','Privacy Policy'),('terms','Terms & Conditions'),
        ('faq','FAQ'),('plans','Investment Plans'),
        ('referral','Referral Program'),
    ]
    slug       = models.CharField(max_length=50, unique=True)
    title      = models.CharField(max_length=200)
    content    = models.TextField(blank=True)
    meta_desc  = models.CharField(max_length=300, blank=True)
    is_active  = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.title
