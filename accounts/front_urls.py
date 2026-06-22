from django.urls import path
from . import front_views as v

urlpatterns = [
    path('', v.home_view, name='front_home'),
    path('about/', v.about_view, name='front_about'),
    path('contact/', v.contact_view, name='front_contact'),
    path('faq/', v.faq_view, name='front_faq'),
    path('how-it-works/', v.how_it_works_view, name='front_how_it_works'),
    path('top-investors/', v.top_investors_view, name='front_top_investors'),
    path('blog/', v.blog_list_view, name='front_blog'),
    path('blog/<slug:slug>/', v.blog_detail_view, name='front_blog_detail'),
    path('privacy-policy/', v.privacy_view, name='front_privacy'),
    path('terms-and-conditions/', v.terms_view, name='front_terms'),
]
