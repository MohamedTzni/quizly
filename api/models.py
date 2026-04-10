"""
Datenbankmodelle für die Quizly-App.
"""

from django.db import models
from django.contrib.auth.models import User


class Quiz(models.Model):
    """Repräsentiert ein aus einem YouTube-Video generiertes Quiz."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} (User: {self.owner.username})"


class Question(models.Model):
    """Eine einzelne Frage innerhalb eines Quizzes mit 4 Antwortmöglichkeiten."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_title = models.CharField(max_length=500)
    question_options = models.JSONField()
    answer = models.CharField(max_length=255)

    def __str__(self):
        return f"Frage: {self.question_title[:60]}"