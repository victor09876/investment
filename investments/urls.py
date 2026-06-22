from django.urls import path
from . import views
urlpatterns = [
    path('plans/',               views.plans_view,           name='plans'),
    path('plans/<slug:slug>/',   views.invest_view,          name='invest'),
    path('my/',                  views.my_investments_view,  name='my_investments'),
    path('cancel/<uuid:pk>/',    views.cancel_investment_view, name='cancel_investment'),
    path('calculator/',          views.roi_calculator_view,  name='calculator'),
]
