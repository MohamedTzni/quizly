from rest_framework.exceptions import PermissionDenied

from .models import Question, Quiz


def create_quiz_with_questions(user, youtube_url, title, description, questions):
    """Saves one generated quiz with all generated questions."""
    quiz = Quiz.objects.create(
        owner=user,
        title=title,
        description=description,
        video_url=youtube_url,
    )
    create_questions(quiz, questions)
    return quiz


def create_questions(quiz, questions):
    """Saves all questions for one quiz."""
    for question in questions:
        Question.objects.create(
            quiz=quiz,
            question_title=question["question_title"],
            question_options=question["question_options"],
            answer=question["answer"],
        )


def get_quiz_for_user(quiz_id, user):
    """Returns a quiz or raises if another user owns it."""
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        return None
    if quiz.owner_id != user.id:
        raise PermissionDenied("You do not have permission to access this quiz.")
    return quiz


def remove_question_timestamps(data):
    """Removes question timestamps from the PATCH response."""
    for question in data["questions"]:
        question.pop("created_at", None)
        question.pop("updated_at", None)
    return data
