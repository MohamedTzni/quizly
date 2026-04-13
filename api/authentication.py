"""
Benutzerdefinierte JWT-Authentifizierung über HTTP-Only-Cookies.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """Liest den Access-Token aus dem HTTP-Only-Cookie statt aus dem Header."""

    def authenticate(self, request):
        """Extrahiert den Token aus dem Cookie und authentifiziert den User."""
        access_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if not access_token:
            return None

        validated_token = self.get_validated_token(access_token)
        return self.get_user(validated_token), validated_token