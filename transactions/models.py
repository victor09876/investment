from django.db import models
from django.conf import settings
import uuid, random, string

class Transaction(models.Model):
    TYPES    = [('deposit','Deposit'),('withdrawal','Withdrawal'),('roi','ROI Profit'),
                ('investment','Investment'),('referral','Referral Bonus'),('refund','Refund')]
    STATUSES = [('pending','Pending'),('processing','Processing'),('completed','Completed'),
                ('failed','Failed'),('cancelled','Cancelled'),('expired','Expired')]
    METHODS  = [('bitcoin','Bitcoin'),('usdt_trc20','USDT TRC20'),('usdt_erc20','USDT ERC20'),
                ('ethereum','Ethereum'),('bank_transfer','Bank Transfer'),
                ('credit_card','Credit Card'),('paypal','PayPal'),('paystack','Paystack'),('wallet','Wallet')]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    txn_id       = models.CharField(max_length=20, unique=True, editable=False)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    type         = models.CharField(max_length=20, choices=TYPES)
    method       = models.CharField(max_length=20, choices=METHODS, blank=True)
    amount       = models.DecimalField(max_digits=18, decimal_places=2)
    fee          = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    net_amount   = models.DecimalField(max_digits=18, decimal_places=2)
    status       = models.CharField(max_length=20, choices=STATUSES, default='pending')
    description  = models.CharField(max_length=255, blank=True)
    reference    = models.CharField(max_length=500, blank=True)
    destination  = models.CharField(max_length=500, blank=True)
    proof_image  = models.ImageField(upload_to='proofs/', null=True, blank=True)
    investment   = models.ForeignKey('investments.Investment', null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='transactions')
    expires_at   = models.DateTimeField(null=True, blank=True)
    card_brand   = models.CharField(max_length=20, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta: ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.txn_id:
            prefix = {'deposit':'DEP','withdrawal':'WTH','roi':'ROI','investment':'INV',
                      'referral':'REF','refund':'RFD'}.get(self.type,'TXN')
            self.txn_id = prefix + ''.join(random.choices(string.digits, k=8))
        if not self.net_amount:
            self.net_amount = self.amount - self.fee
        super().save(*args, **kwargs)

    def __str__(self): return f'{self.txn_id} | {self.type} | ${self.amount}'

    @property
    def is_credit(self): return self.type in ('deposit','roi','referral','refund')

    @property
    def status_class(self):
        return {'completed':'badge-success','processing':'badge-warning',
                'pending':'badge-warning','failed':'badge-danger',
                'cancelled':'badge-danger','expired':'badge-danger'}.get(self.status,'badge-info')

    @property
    def is_expired(self):
        from django.utils import timezone
        return bool(self.expires_at and self.status == 'pending' and timezone.now() > self.expires_at)

    @property
    def time_remaining_seconds(self):
        from django.utils import timezone
        if not self.expires_at or self.status != 'pending':
            return 0
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))


class WalletAddress(models.Model):
    COINS = [('bitcoin','Bitcoin (BTC)'),('usdt_trc20','USDT TRC20'),
             ('usdt_erc20','USDT ERC20'),('ethereum','Ethereum (ETH)')]
    coin      = models.CharField(max_length=20, choices=COINS, unique=True)
    address   = models.CharField(max_length=500)
    label     = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return f'{self.coin}: {self.address[:30]}'
