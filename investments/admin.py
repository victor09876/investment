from django.contrib import admin
from .models import Plan, Investment

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display  = ['name','daily_roi','duration_days','min_amount','max_amount','is_active','is_featured']
    list_editable = ['is_active','is_featured']
    prepopulated_fields = {'slug':('name',)}

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ['user','plan','amount','daily_profit','profit_earned','status','start_date','end_date']
    list_filter  = ['status','plan']
    search_fields= ['user__email']
    readonly_fields = ['id','daily_profit','profit_earned','start_date']
