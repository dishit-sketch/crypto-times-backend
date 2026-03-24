"""Post-MFA-verification login callback for django-mfa2."""

from django.contrib.auth import get_user_model, login
from django.http import HttpResponseRedirect


def login_callback(request, username=None):
    """
    Called by django-mfa2 after successful FIDO2 verification.
    Logs the user in and redirects to the admin dashboard (or ?next= if set).
    """
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        from django.conf import settings
        return HttpResponseRedirect(settings.LOGIN_URL)

    user.backend = "django.contrib.auth.backends.ModelBackend"
    login(request, user)

    next_url = request.POST.get("next") or request.GET.get("next") or "/admin/"
    return HttpResponseRedirect(next_url)
