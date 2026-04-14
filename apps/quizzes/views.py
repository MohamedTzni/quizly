import re
import json
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Quiz
from .serializers import QuizSerializer, QuizUpdateSerializer
from .services import (
    create_quiz_with_questions,
    get_quiz_for_user,
    process_youtube_url,
    remove_question_timestamps,
)
from .utils import is_youtube_url


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
            return Response({"detail": "A YouTube URL is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not is_youtube_url(youtube_url):
            return Response({"detail": "Only YouTube URLs are allowed."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            title, description, questions = process_youtube_url(youtube_url)
        except (ValueError, json.JSONDecodeError, OSError) as exc:
            clean_error = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
            return Response({"detail": f"Error processing video: {clean_error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        quiz = create_quiz_with_questions(request.user, youtube_url, title, description, questions)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuizDetailView(APIView):
    """Gets, updates or deletes a single quiz."""

    def get(self, request, pk):
        """Returns a single quiz with all its questions."""
        quiz = get_quiz_for_user(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QuizSerializer(quiz)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        """Updates the title and/or description of a quiz."""
        quiz = get_quiz_for_user(pk, request.user)
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
        quiz = get_quiz_for_user(pk, request.user)
        if quiz is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        quiz.delete()
        return Response(None, status=status.HTTP_204_NO_CONTENT)
