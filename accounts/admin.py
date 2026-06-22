from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Notification, SiteSettings, RegistrationCode

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email','full_name','wallet_balance','profit_balance','is_kyc_verified','is_active','date_joined']
    list_filter  = ['is_active','is_staff','is_kyc_verified','kyc_status']
    search_fields= ['email','first_name','last_name','phone']
    ordering     = ['-date_joined']
    fieldsets = (
        (None, {'fields':('email','password')}),
        ('Personal', {'fields':('first_name','last_name','phone','country','address','date_of_birth','gender','avatar')}),
        ('Balances', {'fields':('wallet_balance','profit_balance')}),
        ('KYC', {'fields':('is_kyc_verified','kyc_status')}),
        ('Referral', {'fields':('referral_code','referred_by')}),
        ('Security', {'fields':('withdrawal_pin',)}),
        ('Permissions', {'fields':('is_active','is_staff','is_superuser','groups','user_permissions')}),
    )
    add_fieldsets = ((None,{'classes':('wide',),'fields':('email','first_name','last_name','password1','password2')}),)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title','user','type','is_read','created_at']
    list_filter  = ['type','is_read']
    search_fields= ['title','user__email']

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return not SiteSettings.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    list_display = ['code','label','is_active','times_used','max_uses','expires_at','created_at']
    list_editable= ['is_active']
