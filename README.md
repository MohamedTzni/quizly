# Quizly Backend

This project was created as part of the Fullstack Developer training at Developer Akademie.
The frontend was provided and can be found here: https://github.com/Developer-Akademie-Backendkurs/project.Quizly

Backend for Quizly – a tool that automatically generates quizzes from YouTube videos.

## Requirements

**FFMPEG** must be installed globally – required by Whisper AI for audio processing.

Windows:
winget install --id Gyan.FFmpeg -e --source winget

macOS:
brew install ffmpeg

## Setup

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Rename .env.example to .env and fill in the values:

SECRET_KEY=
GEMINI_API_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

Then:

python manage.py migrate
python manage.py runserver

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/register/ | Register |
| POST | /api/login/ | Login |
| POST | /api/logout/ | Logout |
| POST | /api/token/refresh/ | Refresh token |
| GET | /api/quizzes/ | Get all quizzes |
| POST | /api/quizzes/ | Create quiz |
| GET | /api/quizzes/{id}/ | Get single quiz |
| PATCH | /api/quizzes/{id}/ | Update quiz |
| DELETE | /api/quizzes/{id}/ | Delete quiz |