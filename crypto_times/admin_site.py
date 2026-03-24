"""
Custom AdminSite that requires FIDO2 for superusers.

Regular staff users log in normally (username + password only).
Superusers are redirected to FIDO2 verification after their password
is accepted — but only if they have already registered a security key.
Superusers without a registered key still log in normally so they can
visit /mfa/fido2/ to register one.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm


class MFAAdminSite(AdminSite):
    def login(self, request, extra_context=None):
        if request.method == "POST":
            form = AdminAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if user.is_superuser:
                    from mfa.helpers import has_mfa
                    mfa_response = has_mfa(request, user.username)
                    if mfa_response:
                        # Preserve the post-login destination for login_callback
                        request.session["mfa_next"] = request.POST.get("next", "/admin/")
                        return mfa_response
                    # Superuser has no registered key yet — fall through to normal login
        return super().login(request, extra_context)
