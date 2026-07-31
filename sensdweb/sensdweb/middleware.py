from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse


class LoginRequiredMiddleware:
    """Require authentication for the SENSD application by default."""

    PUBLIC_PREFIXES = (
        "/authentication/",
        "/admin/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        static_url = settings.STATIC_URL or "/static/"
        media_url = settings.MEDIA_URL or "/media/"
        is_public = request.path.startswith(
            self.PUBLIC_PREFIXES + (static_url, media_url)
        )

        if not request.user.is_authenticated and not is_public:
            return redirect_to_login(request.get_full_path(), reverse("login"))

        return self.get_response(request)
