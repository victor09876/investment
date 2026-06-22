from django.contrib import admin
from .models import Transaction, WalletAddress
from django.utils import timezone

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ['txn_id','user','type','method','amount','status','created_at']
    list_filter   = ['type','status','method']
    search_fields = ['txn_id','user__email','reference']
    readonly_fields = ['id','txn_id','created_at']
    list_editable  = ['status']
    actions = ['approve_deposits','approve_withdrawals']

    def approve_deposits(self, request, queryset):
        updated = 0
        for txn in queryset.filter(type='deposit', status='pending'):
            txn.status = 'completed'; txn.processed_at = timezone.now(); txn.save()
            txn.user.wallet_balance += txn.net_amount
            txn.user.save(update_fields=['wallet_balance'])
            updated += 1
        self.message_user(request, f'{updated} deposit(s) approved and credited.')
    approve_deposits.short_description = 'Approve & credit selected deposits'

    def approve_withdrawals(self, request, queryset):
        updated = 0
        for txn in queryset.filter(type='withdrawal', status__in=['pending','processing']):
            txn.status = 'completed'; txn.processed_at = timezone.now(); txn.save()
            updated += 1
        self.message_user(request, f'{updated} withdrawal(s) marked as completed.')
    approve_withdrawals.short_description = 'Mark selected withdrawals as completed'

@admin.register(WalletAddress)
class WalletAddressAdmin(admin.ModelAdmin):
    list_display = ['coin','address','is_active']
    list_editable= ['is_active']
