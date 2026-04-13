from django.contrib import admin
from .models import Quiz, Question


class QuestionInline(admin.TabularInline):
    """Shows questions directly inside the quiz form."""

    model = Question
    extra = 0
    fields = ["question_title", "question_options", "answer"]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin view for quizzes with questions shown inline."""

    list_display = ["title", "owner", "created_at", "updated_at"]
    list_filter = ["owner", "created_at"]
    search_fields = ["title", "owner__username"]
    inlines = [QuestionInline]
    readonly_fields = ["created_at", "updated_at", "video_url"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin view for single quiz questions."""

    list_display = ["question_title", "quiz", "answer"]
    list_filter = ["quiz"]
    search_fields = ["question_title", "quiz__title"]
