from .models import SiteSettings, Branding


def site_context(request):
    """Injects site settings and branding into every template."""
    try:
        settings = SiteSettings.get()
    except Exception:
        settings = None
    try:
        branding = Branding.get()
    except Exception:
        branding = None

    # Unread notification count for authenticated users
    unread_count = 0
    if request.user.is_authenticated:
        try:
            from .models import Notification
            unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        except Exception:
            pass

    return {
        'site_settings': settings,
        'branding': branding,
        'global_unread': unread_count,
    }
