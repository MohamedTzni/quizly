# Quizly Backend

Backend für Quizly – ein Tool das aus YouTube-Videos automatisch Quizze generiert.

## Voraussetzungen

**FFMPEG** muss global installiert sein (wird von Whisper AI benötigt):

Windows:
```powershell
winget install --id Gyan.FFmpeg -e --source winget
```

macOS:
```bash
brew install ffmpeg
```

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`.env.example` zu `.env` umbenennen und ausfüllen:
SECRET_KEY=
GEMINI_API_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

Dann:

```powershell
python manage.py migrate
python manage.py runserver
```

## API Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| POST | `/api/register/` | Registrieren |
| POST | `/api/login/` | Einloggen |
| POST | `/api/logout/` | Ausloggen |
| POST | `/api/token/refresh/` | Token erneuern |
| GET | `/api/quizzes/` | Alle Quizze |
| POST | `/api/quizzes/` | Quiz erstellen |
| GET | `/api/quizzes/{id}/` | Quiz abrufen |
| PATCH | `/api/quizzes/{id}/` | Quiz bearbeiten |
| DELETE | `/api/quizzes/{id}/` | Quiz löschen |