from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from an HTTP-only cookie instead of the header."""

    def authenticate(self, request):
        """Extracts the token from the cookie and authenticates the user."""
        access_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"])
        if not access_token:
            return None
        validated_token = self.get_validated_token(access_token)
        return self.get_user(validated_token), validated_token
