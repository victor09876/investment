from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',       views.dashboard_view,        name='dashboard'),
    path('register/',        views.register_view,         name='register'),
    path('login/',           views.login_view,            name='login'),
    path('logout/',          views.logout_view,           name='logout'),
    path('forgot-password/', views.forgot_password_view,  name='forgot_password'),
    path('profile/',         views.profile_view,          name='profile'),
    path('settings/',        views.settings_view,         name='settings'),
    path('change-password/', views.change_password_view,  name='change_password'),
    path('set-pin/',         views.set_pin_view,          name='set_pin'),
    path('notifications/',   views.notifications_view,    name='notifications'),
    path('api/notifications/', views.notifications_api,   name='notifications_api'),
    path('login-history/',   views.login_history_view,    name='login_history'),
    path('kyc/',             views.kyc_view,              name='kyc'),
    path('referrals/',       views.referrals_view,        name='referrals'),
    path('ranking/',         views.ranking_view,          name='ranking'),
    path('transfer/',        views.transfer_view,         name='transfer'),
    path('tickets/',         views.tickets_view,          name='tickets'),
    path('tickets/<uuid:pk>/', views.ticket_detail_view,  name='ticket_detail'),
    path('statement/',       views.statement_view,        name='statement'),
]
