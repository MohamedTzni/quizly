from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Quiz, Question


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    confirmed_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirmed_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        """Checks that password and confirmation match."""
        if data["password"] != data["confirmed_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        """Checks that the email is not already taken."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        """Creates a new user with a hashed password."""
        validated_data.pop("confirmed_password")
        user = User.objects.create_user(**validated_data)
        return user


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for a single quiz question."""

    answer = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_answer(self, obj):
        labels = ["A", "B", "C", "D"]
        if obj.answer in labels:
            answer_index = labels.index(obj.answer)
            if answer_index < len(obj.question_options):
                return obj.question_options[answer_index]
        return obj.answer


class QuizSerializer(serializers.ModelSerializer):
    """Full serializer for a quiz including its questions."""

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
    """Serializer for updating title and description."""

    class Meta:
        model = Quiz
        fields = ["id", "title", "description"]
