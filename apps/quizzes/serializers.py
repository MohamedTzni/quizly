from rest_framework import serializers

from .models import Quiz, Question


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
        """Returns the answer text instead of the answer label."""
        if obj.answer == "A":
            return obj.question_options[0]
        elif obj.answer == "B":
            return obj.question_options[1]
        elif obj.answer == "C":
            return obj.question_options[2]
        elif obj.answer == "D":
            return obj.question_options[3]
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
