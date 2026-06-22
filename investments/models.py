from django.db import models
from django.conf import settings
from decimal import Decimal
import uuid

class Plan(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name         = models.CharField(max_length=100)
    slug         = models.SlugField(unique=True)
    icon         = models.CharField(max_length=30, default='gem',
                                     help_text="Font Awesome icon name, e.g. 'gem', 'rocket', 'chart-line' (without the fa- prefix)")
    description  = models.TextField(blank=True)
    daily_roi    = models.DecimalField(max_digits=5, decimal_places=2)
    duration_days= models.PositiveIntegerField()
    min_amount   = models.DecimalField(max_digits=18, decimal_places=2)
    max_amount   = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    referral_bonus_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    is_active    = models.BooleanField(default=True)
    is_featured  = models.BooleanField(default=False)
    sort_order   = models.PositiveIntegerField(default=0)

    class Meta: ordering = ['sort_order', 'min_amount']

    def __str__(self): return self.name

    @property
    def fa_icon(self):
        """Return a safe Font Awesome icon name. Falls back to 'gem' for legacy emoji values."""
        val = (self.icon or '').strip()
        # If it's a legacy emoji or empty, fall back to a sensible default
        if not val or not all(c.isalnum() or c == '-' for c in val):
            return 'gem'
        return val

    def daily_profit_for(self, amount):
        return Decimal(str(amount)) * self.daily_roi / 100

    def total_profit_for(self, amount):
        return self.daily_profit_for(amount) * self.duration_days

    def total_return_for(self, amount):
        return Decimal(str(amount)) + self.total_profit_for(amount)


class Investment(models.Model):
    STATUS = [('active','Active'),('completed','Completed'),('cancelled','Cancelled')]
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='investments')
    plan         = models.ForeignKey(Plan, on_delete=models.PROTECT)
    amount       = models.DecimalField(max_digits=18, decimal_places=2)
    daily_profit = models.DecimalField(max_digits=18, decimal_places=2)
    profit_earned= models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status       = models.CharField(max_length=20, choices=STATUS, default='active')
    start_date   = models.DateTimeField(auto_now_add=True)
    end_date     = models.DateTimeField()
    last_roi_date= models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta: ordering = ['-created_at']

    def __str__(self): return f'{self.user.email} – {self.plan.name} – ${self.amount}'

    @property
    def progress_pct(self):
        from django.utils import timezone
        total = max((self.end_date - self.start_date).days, 1)
        elapsed = (timezone.now() - self.start_date).days
        return min(round((elapsed / total) * 100, 1), 100)

    @property
    def days_remaining(self):
        from django.utils import timezone
        return max((self.end_date - timezone.now()).days, 0)

    @property
    def expected_total(self):
        return self.amount + (self.daily_profit * self.plan.duration_days)

    @property
    def short_id(self):
        return str(self.id).replace('-','')[:8].upper()
