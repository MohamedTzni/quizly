from django.conf import settings


def set_auth_cookies(response, refresh):
    """Sets access and refresh tokens as HTTP-only cookies."""
    jwt = settings.SIMPLE_JWT
    set_access_cookie(response, refresh, jwt)
    set_refresh_cookie(response, refresh, jwt)


def set_access_cookie(response, refresh, jwt):
    """Sets the access token cookie."""
    response.set_cookie(
        jwt["AUTH_COOKIE"],
        str(refresh.access_token),
        httponly=jwt["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt["AUTH_COOKIE_SAMESITE"],
        secure=jwt["AUTH_COOKIE_SECURE"],
        max_age=int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds()),
    )


def set_refresh_cookie(response, refresh, jwt):
    """Sets the refresh token cookie."""
    response.set_cookie(
        jwt["REFRESH_COOKIE"],
        str(refresh),
        httponly=jwt["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt["AUTH_COOKIE_SAMESITE"],
        secure=jwt["AUTH_COOKIE_SECURE"],
        max_age=int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


def delete_auth_cookies(response):
    """Deletes the auth cookies from the response."""
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"])
    response.delete_cookie(settings.SIMPLE_JWT["REFRESH_COOKIE"])
