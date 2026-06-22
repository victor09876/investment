from django.urls import path
from . import views
urlpatterns = [
    path('deposit/',    views.deposit_view,      name='deposit'),
    path('withdrawal/', views.withdrawal_view,   name='withdrawal'),
    path('history/',    views.transactions_view, name='transactions'),
]
