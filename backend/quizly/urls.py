"""
URL configuration for the Quizly project.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

frontend_dir = settings.BASE_DIR.parent / "frontend"
urlpatterns += [
    path("", RedirectView.as_view(url="/pages/login.html", permanent=False)),
    path("frontend/", RedirectView.as_view(url="/frontend/pages/login.html", permanent=False)),
    re_path(
        r"^frontend/(?P<path>(?:assets|shared|pages)/.*|styles\.css|script\.js|index\.html)$",
        serve,
        {"document_root": frontend_dir},
    ),
    re_path(
        r"^(?P<path>(?:assets|shared|pages)/.*|styles\.css|script\.js|index\.html)$",
        serve,
        {"document_root": frontend_dir},
    ),
]
