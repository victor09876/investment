"""
Email sending helper.

If the admin has configured SMTP settings (Settings > Email), emails are sent
via that SMTP server. Otherwise, falls back to Django's console backend
(EMAIL_BACKEND in settings.py), which prints emails to the server console/logs
— useful for development and for hosts where SMTP hasn't been set up yet.
"""
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings as django_settings


def get_email_connection():
    """Return an email connection — SMTP if configured in SiteSettings, else console."""
    from .models import SiteSettings
    site = SiteSettings.get()

    if site.smtp_host and site.smtp_username:
        return get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=site.smtp_host,
            port=site.smtp_port or 587,
            username=site.smtp_username,
            password=site.smtp_password,
            use_tls=site.smtp_use_tls,
        )
    return get_connection(backend=django_settings.EMAIL_BACKEND)


def send_email(to_email, subject, template_name, context=None):
    """
    Send an HTML email using a template from templates/emails/.
    `template_name` should be the base name without extension, e.g. 'password_reset'
    — this will render templates/emails/{template_name}.html
    """
    from .models import SiteSettings
    site = SiteSettings.get()
    context = context or {}
    context['site'] = site
    context['site_name'] = site.site_name or 'InvestPro'

    html_body = render_to_string(f'emails/{template_name}.html', context)
    from_email = f'{site.email_from_name or site.site_name or "InvestPro"} <{site.company_email or django_settings.DEFAULT_FROM_EMAIL}>'

    connection = get_email_connection()
    msg = EmailMultiAlternatives(
        subject=subject, body=html_body, from_email=from_email,
        to=[to_email], connection=connection,
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)
