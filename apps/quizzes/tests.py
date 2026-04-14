from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Question, Quiz
from .utils import is_youtube_url


def get_question_options():
    """Returns four simple answer options."""
    return ["Option A", "Option B", "Option C", "Option D"]


def get_question_data(number):
    """Returns one question for mocked quiz generation."""
    return {
        "question_title": f"Question {number}",
        "question_options": get_question_options(),
        "answer": "Option A",
    }


def get_mock_questions():
    """Returns 10 mocked quiz questions."""
    questions = []
    for number in range(10):
        questions.append(get_question_data(number + 1))
    return questions


class QuizDetailPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="Test1234!")
        self.other_user = User.objects.create_user(username="other", password="Test1234!")
        self.quiz = self.create_quiz()
        self.create_question()
        self.url = reverse("quiz-detail", args=[self.quiz.id])

    def create_quiz(self):
        return Quiz.objects.create(
            owner=self.owner,
            title="Owner Quiz",
            description="Private quiz",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

    def create_question(self):
        Question.objects.create(
            quiz=self.quiz,
            question_title="Question 1",
            question_options=get_question_options(),
            answer="Option A",
        )

    def test_get_other_users_quiz_returns_403(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_other_users_quiz_returns_403(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(self.url, {"title": "Changed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_other_users_quiz_returns_403(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Quiz.objects.filter(id=self.quiz.id).exists())

    def test_patch_own_quiz_returns_full_quiz_details(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.url,
            {"title": "Partially Updated Title", "description": "Partially Updated Description"},
            format="json",
        )
        self.assert_patch_quiz_fields(response)
        self.assert_patch_question_fields(response)

    def assert_patch_quiz_fields(self, response):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Partially Updated Title")
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)
        self.assertEqual(
            response.data["video_url"],
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

    def assert_patch_question_fields(self, response):
        self.assertEqual(response.data["questions"][0]["question_title"], "Question 1")
        self.assertEqual(
            response.data["questions"][0]["question_options"],
            get_question_options(),
        )
        self.assertEqual(response.data["questions"][0]["answer"], "Option A")
        self.assertNotIn("created_at", response.data["questions"][0])
        self.assertNotIn("updated_at", response.data["questions"][0])


class QuizCreateTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="Test1234!")
        self.url = reverse("quiz-list-create")

    @patch("apps.quizzes.views.process_youtube_url")
    def test_create_quiz_returns_question_timestamps(self, mock_process_youtube_url):
        questions = get_mock_questions()
        mock_process_youtube_url.return_value = self.get_mock_quiz(questions)
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.url,
            {"url": "https://www.youtube.com/watch?v=example"},
            format="json",
        )
        self.assert_create_response(response)

    def get_mock_quiz(self, questions):
        return ("Generated Quiz", "Quiz Description", questions)

    def assert_create_response(self, response):
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("created_at", response.data["questions"][0])
        self.assertIn("updated_at", response.data["questions"][0])
        self.assertEqual(len(response.data["questions"]), 10)

    def test_youtube_url_check(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=example"))
        self.assertTrue(is_youtube_url("https://youtu.be/example"))
        self.assertFalse(is_youtube_url("https://example.com/video"))

    def test_create_quiz_rejects_non_youtube_url(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"url": "https://example.com/video"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
