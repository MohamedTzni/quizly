"""
Views für die Quizly REST API.
Jede View returnt ausschließlich eine HTTP Response.
"""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Quiz, Question
from .serializers import RegisterSerializer, QuizSerializer, QuizUpdateSerializer
from .utils import process_youtube_url


def set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Setzt Access- und Refresh-Token als HTTP-Only-Cookies in die Response."""
    jwt_settings = settings.SIMPLE_JWT
    response.set_cookie(
        key=jwt_settings["AUTH_COOKIE"],
        value=str(refresh.access_token),
        httponly=jwt_settings["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt_settings["AUTH_COOKIE_SAMESITE"],
        secure=jwt_settings["AUTH_COOKIE_SECURE"],
        max_age=int(jwt_settings["ACCESS_TOKEN_LIFETIME"].total_seconds()),
    )
    response.set_cookie(
        key=jwt_settings["REFRESH_COOKIE"],
        value=str(refresh),
        httponly=jwt_settings["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt_settings["AUTH_COOKIE_SAMESITE"],
        secure=jwt_settings["AUTH_COOKIE_SECURE"],
        max_age=int(jwt_settings["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


def delete_auth_cookies(response: Response) -> None:
    """Löscht Access- und Refresh-Cookie aus der Response."""
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"])
    response.delete_cookie(settings.SIMPLE_JWT["REFRESH_COOKIE"])


class RegisterView(APIView):
    """Registriert einen neuen Benutzer."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Erstellt einen neuen User nach Validierung."""
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Meldet einen Benutzer an und setzt JWT-Cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validiert Credentials und gibt JWT-Cookies zurück."""
        from django.contrib.auth import authenticate

        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "detail": "Login successfully!",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """Meldet den Benutzer ab, blacklistet den Refresh-Token und löscht Cookies."""

    def post(self, request):
        """Blacklistet den Refresh-Token und löscht die Cookies."""
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["REFRESH_COOKIE"])
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass

        response = Response(
            {"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    """Erneuert den Access-Token anhand des Refresh-Tokens aus dem Cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Liest den Refresh-Cookie und stellt einen neuen Access-Token aus."""
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["REFRESH_COOKIE"])
        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(refresh_token)
            response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
            set_auth_cookies(response, refresh)
            return response
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class QuizListCreateView(APIView):
    """Listet alle Quizze des Users oder erstellt ein neues aus einer YouTube-URL."""

    def get(self, request):
        """Gibt alle Quizze des eingeloggten Users zurück."""
        quizzes = Quiz.objects.filter(owner=request.user)
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Erstellt ein Quiz aus einer YouTube-URL via KI-Pipeline."""
        youtube_url = request.data.get("url", "").strip()
        if not youtube_url:
            return Response(
                {"detail": "A YouTube URL is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            title, description, questions = process_youtube_url(youtube_url)
        except Exception as exc:
            return Response(
                {"detail": f"Error processing video: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        quiz = Quiz.objects.create(
            owner=request.user,
            title=title,
            description=description,
            video_url=youtube_url,
        )
        for question_data in questions:
            Question.objects.create(
                quiz=quiz,
                question_title=question_data["question_title"],
                question_options=question_data["question_options"],
                answer=question_data["answer"],
            )

        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(APIView):
    """Ruft ein einzelnes Quiz ab, bearbeitet oder löscht es."""

    def get_quiz(self, quiz_id: int, user):
        """Holt das Quiz und prüft die Eigentümerschaft."""
        try:
            return Quiz.objects.get(id=quiz_id, owner=user)
        except Quiz.DoesNotExist:
            return None

    def get(self, request, pk):
        """Gibt ein einzelnes Quiz mit allen Fragen zurück."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """Aktualisiert Titel und/oder Beschreibung eines Quizzes."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuizUpdateSerializer(quiz, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Löscht ein Quiz dauerhaft."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        quiz.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)