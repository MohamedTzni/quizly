from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .utils import delete_auth_cookies, set_auth_cookies
from .serializers import RegisterSerializer


class RegisterView(APIView):
    """Handles user registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Creates a new user if the data is valid."""
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({"detail": "User created successfully!"}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Handles user login."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Checks credentials and sets JWT cookies."""
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        user_data = {"id": user.id, "username": user.username, "email": user.email}
        response_data = {"detail": "Login successfully!", "user": user_data}
        response = Response(response_data, status=status.HTTP_200_OK)
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Handles user logout."""

    def post(self, request):
        """Blacklists the refresh token and deletes the cookies."""
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["REFRESH_COOKIE"])
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass  # Token already invalid or missing — cookies are deleted regardless
        response = Response(
            {"detail": "Log-Out successfully! Tokens will be deleted."},
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Refreshes the access token using the refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Reads the refresh cookie and issues a new access token."""
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["REFRESH_COOKIE"])
        if not refresh_token:
            return Response({"detail": "Refresh token not found."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(refresh_token)
            response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
            set_auth_cookies(response, refresh)
            return response
        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
