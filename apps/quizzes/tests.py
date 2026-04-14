import os
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Question, Quiz
from .services import process_youtube_url
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

    @patch("apps.quizzes.views.process_youtube_url")
    def test_create_quiz_returns_json_error_when_generation_fails(self, mock_process_youtube_url):
        mock_process_youtube_url.side_effect = RuntimeError("Download timed out")
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            self.url,
            {"url": "https://www.youtube.com/watch?v=example"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["detail"], "Error processing video: Download timed out")


class QuizGenerationTests(APITestCase):
    @patch("yt_dlp.YoutubeDL")
    def test_download_audio_reads_title_before_download(self, mock_youtube_dl):
        from .services import download_audio

        ydl = mock_youtube_dl.return_value.__enter__.return_value
        ydl.extract_info.return_value = {"title": "Real YouTube Video Title"}

        audio_path, video_title = download_audio("https://youtu.be/example", ".")

        self.assertEqual(audio_path, ".\\audio.wav" if os.name == "nt" else "./audio.wav")
        self.assertEqual(video_title, "Real YouTube Video Title")
        ydl.extract_info.assert_called_once_with("https://youtu.be/example", download=False)
        ydl.download.assert_called_once_with(["https://youtu.be/example"])

    def test_get_ydl_options_limits_retries_and_timeout(self):
        from .services import get_ydl_options

        options = get_ydl_options(".")

        self.assertTrue(options["noplaylist"])
        self.assertEqual(options["proxy"], "")
        self.assertFalse(options["continuedl"])
        self.assertEqual(options["socket_timeout"], 20)
        self.assertEqual(options["retries"], 2)
        self.assertEqual(options["fragment_retries"], 2)
        self.assertEqual(options["extractor_retries"], 2)

    @patch("apps.quizzes.services.generate_quiz_from_transcript")
    @patch("apps.quizzes.services.transcribe_audio")
    @patch("apps.quizzes.services.download_audio")
    @patch("apps.quizzes.services.shutil.rmtree")
    @patch("apps.quizzes.services.create_quiz_temp_dir")
    def test_process_youtube_url_uses_video_title(
        self,
        mock_create_quiz_temp_dir,
        mock_rmtree,
        mock_download_audio,
        mock_transcribe_audio,
        mock_generate_quiz,
    ):
        mock_create_quiz_temp_dir.return_value = "."
        mock_download_audio.return_value = ("audio.wav", "Real YouTube Video Title")
        mock_transcribe_audio.return_value = "Transcript text"
        mock_generate_quiz.return_value = get_mock_questions()

        title, description, questions = process_youtube_url("https://youtu.be/example")

        self.assertEqual(title, "Quiz - Real YouTube Video Title")
        self.assertEqual(description, "Transcript text...")
        self.assertEqual(len(questions), 10)
        mock_rmtree.assert_called_once_with(".", ignore_errors=True)
