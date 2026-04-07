"""
Serializer für die Quizly REST API.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Quiz, Question


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer für die Benutzerregistrierung."""

    confirmed_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirmed_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        """Prüft, ob Passwort und Bestätigung übereinstimmen."""
        if data["password"] != data["confirmed_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        """Prüft, ob die E-Mail bereits vergeben ist."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        """Erstellt einen neuen Benutzer mit gehashtem Passwort."""
        validated_data.pop("confirmed_password")
        user = User.objects.create_user(**validated_data)
        return user


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer für einzelne Quizfragen."""

    class Meta:
        model = Question
        fields = ["id", "question_title", "question_options", "answer"]


class QuizSerializer(serializers.ModelSerializer):
    """Vollständiger Serializer für ein Quiz inklusive Fragen."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "video_url", "questions"]


class QuizUpdateSerializer(serializers.ModelSerializer):
    """Serializer für das Bearbeiten von Titel und Beschreibung."""

    class Meta:
        model = Quiz
        fields = ["id", "title", "description"]