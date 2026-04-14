from django.apps import AppConfig


class QuizzesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    label = "api"
    name = "apps.quizzes"
    verbose_name = "Quizzes"
