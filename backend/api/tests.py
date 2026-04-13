from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Question, Quiz
from .utils import is_youtube_url


class QuizDetailPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="Test1234!")
        self.other_user = User.objects.create_user(username="other", password="Test1234!")
        self.quiz = Quiz.objects.create(
            owner=self.owner,
            title="Owner Quiz",
            description="Private quiz",
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        Question.objects.create(
            quiz=self.quiz,
            question_title="Question 1",
            question_options=["Option A", "Option B", "Option C", "Option D"],
            answer="Option A",
        )
        self.url = reverse("quiz-detail", args=[self.quiz.id])

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Partially Updated Title")
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)
        self.assertEqual(
            response.data["video_url"],
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        self.assertEqual(response.data["questions"][0]["question_title"], "Question 1")
        self.assertEqual(
            response.data["questions"][0]["question_options"],
            ["Option A", "Option B", "Option C", "Option D"],
        )
        self.assertEqual(response.data["questions"][0]["answer"], "Option A")
        self.assertNotIn("created_at", response.data["questions"][0])
        self.assertNotIn("updated_at", response.data["questions"][0])


class QuizCreateTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="Test1234!")
        self.url = reverse("quiz-list-create")

    @patch("api.views.process_youtube_url")
    def test_create_quiz_returns_question_timestamps(self, mock_process_youtube_url):
        questions = []
        for number in range(10):
            questions.append(
                {
                    "question_title": f"Question {number + 1}",
                    "question_options": [
                        "Option A",
                        "Option B",
                        "Option C",
                        "Option D",
                    ],
                    "answer": "Option A",
                }
            )
        mock_process_youtube_url.return_value = (
            "Generated Quiz",
            "Quiz Description",
            questions,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"url": "https://www.youtube.com/watch?v=example"},
            format="json",
        )

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
