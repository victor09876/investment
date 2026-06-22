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

    # Sidebar menu visibility map (staff always see everything)
    sidebar_visible = {}
    try:
        from .models import SidebarMenuItem
        hidden_keys = set(SidebarMenuItem.objects.filter(is_visible=False).values_list('key', flat=True))
        if request.user.is_authenticated and request.user.is_staff:
            hidden_keys = set()
        sidebar_visible = {'hidden': hidden_keys}
    except Exception:
        sidebar_visible = {'hidden': set()}

    return {
        'site_settings': settings,
        'branding': branding,
        'global_unread': unread_count,
        'sidebar_visible': sidebar_visible,
    }
