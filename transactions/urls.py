from django.urls import path
from . import views
urlpatterns = [
    path('deposit/',    views.deposit_view,      name='deposit'),
    path('paystack/callback/', views.paystack_callback_view, name='paystack_callback'),
    path('withdrawal/', views.withdrawal_view,   name='withdrawal'),
    path('history/',    views.transactions_view, name='transactions'),
]
