import re
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Quiz
from .serializers import RegisterSerializer, QuizSerializer, QuizUpdateSerializer
from .utils import (
    create_questions,
    create_quiz,
    delete_auth_cookies,
    is_youtube_url,
    process_youtube_url,
    remove_question_timestamps,
    set_auth_cookies,
)


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
            pass
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
            data = {"detail": "Refresh token not found."}
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)
        try:
            return self.create_refresh_response(refresh_token)
        except TokenError:
            data = {"detail": "Invalid or expired refresh token."}
            return Response(data, status=status.HTTP_401_UNAUTHORIZED)

    def create_refresh_response(self, refresh_token):
        """Creates a new access token response."""
        refresh = RefreshToken(refresh_token)
        response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
        set_auth_cookies(response, refresh)
        return response


class QuizListCreateView(APIView):
    """Lists all quizzes or creates a new one from a YouTube URL."""

    def get(self, request):
        """Returns all quizzes of the logged-in user."""
        quizzes = Quiz.objects.filter(owner=request.user)
        serializer = QuizSerializer(quizzes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Creates a quiz from a YouTube URL."""
        youtube_url = request.data.get("url", "").strip()
        if not youtube_url:
            data = {"detail": "A YouTube URL is required."}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        if not is_youtube_url(youtube_url):
            data = {"detail": "Only YouTube URLs are allowed."}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        return self.create_quiz_response(request, youtube_url)

    def create_quiz_response(self, request, youtube_url):
        """Creates the quiz and returns the API response."""
        try:
            title, description, questions = process_youtube_url(youtube_url)
        except Exception as exc:
            clean_error = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
            return Response(
                {"detail": f"Error processing video: {clean_error}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        quiz = create_quiz(request.user, youtube_url, title, description)
        create_questions(quiz, questions)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(APIView):
    """Gets, updates or deletes a single quiz."""

    def get_quiz(self, quiz_id, user):
        """Returns the quiz, rejects access if it belongs to another user."""
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return None
        if quiz.owner_id != user.id:
            raise PermissionDenied("You do not have permission to access this quiz.")
        return quiz

    def get(self, request, pk):
        """Returns a single quiz with all its questions."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """Updates the title and/or description of a quiz."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuizUpdateSerializer(quiz, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        data = QuizSerializer(quiz).data
        data = remove_question_timestamps(data)
        return Response(data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        """Deletes a quiz permanently."""
        quiz = self.get_quiz(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        quiz.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
