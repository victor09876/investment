from django.shortcuts import render
from django.urls import reverse


class MaintenanceModeMiddleware:
    """If maintenance mode is enabled, show maintenance page to non-staff users."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from .models import SiteSettings
            settings = SiteSettings.get()
        except Exception:
            return self.get_response(request)

        if settings.maintenance_mode and not (request.user.is_authenticated and request.user.is_staff):
            allowed_paths = ['/login/', '/logout/', '/panel/']
            if not any(request.path.startswith(p) for p in allowed_paths):
                return render(request, 'maintenance.html', {'settings': settings}, status=503)

        return self.get_response(request)


class CronTickMiddleware:
    """Runs scheduled tasks (ROI crediting, deposit expiry) automatically on a
    timed interval, simulating a cron job without needing OS-level cron access.

    Checks on each request whether `cron_interval_minutes` has elapsed since the
    last tick and, if so, runs all cron tasks. This keeps the check itself very
    cheap (a single SiteSettings read) so normal requests aren't slowed down.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from .cron_tasks import cron_due, run_all_cron_tasks
            if cron_due():
                run_all_cron_tasks(trigger='auto')
        except Exception:
            pass  # never let cron errors break a request

        return self.get_response(request)
