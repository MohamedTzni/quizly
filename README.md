# Quizly Backend

Quizly is a Django REST API for creating quizzes from YouTube videos. A user submits a YouTube URL, the backend extracts the audio, transcribes it locally with Whisper and asks Gemini to generate quiz questions from the transcript.

The matching frontend template is provided by Developer Akademie:
https://github.com/Developer-Akademie-Backendkurs/project.Quizly

## What The Backend Does

1. Receives a YouTube URL from an authenticated user.
2. Validates that the URL belongs to YouTube.
3. Downloads the audio with `yt-dlp`.
4. Converts the audio with FFmpeg.
5. Transcribes the audio locally with Whisper.
6. Sends the transcript to Gemini.
7. Stores the generated quiz and questions in the database.

Each generated quiz contains 10 questions with 4 answer options.

## Tech Stack

| Area | Tool |
| --- | --- |
| API | Django REST Framework |
| Authentication | Simple JWT with HTTP-only cookies |
| Audio download | `yt-dlp` |
| Audio conversion | FFmpeg |
| Transcription | Whisper |
| Quiz generation | Gemini Flash |
| Database | SQLite for local development |

## Project Structure

```text
backend/
  core/
    settings.py
    urls.py
    wsgi.py
  apps/
    accounts/
      authentication.py
      cookies.py
      serializers.py
      urls.py
      views.py
    quizzes/
      admin.py
      generation.py
      models.py
      serializers.py
      services.py
      tests.py
      urls.py
      validators.py
  manage.py
  requirements.txt
```

`core` contains the Django project configuration. `accounts` handles registration, login, logout, token refresh and cookie-based JWT authentication. `quizzes` contains the quiz domain, including models, API views, database services, validation and the YouTube-to-quiz generation pipeline.

## Requirements

- Python 3.10+
- FFmpeg installed globally
- Gemini API key
- Optional: Node.js, if YouTube requires a JavaScript runtime for `yt-dlp`

Install FFmpeg on Windows:

```powershell
winget install --id Gyan.FFmpeg -e --source winget
```

Install FFmpeg on macOS:

```bash
brew install ffmpeg
```

## Local Setup

Clone the repository:

```powershell
git clone https://github.com/MohamedTzni/quizly.git
cd quizly\backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:

```env
SECRET_KEY=your-django-secret-key-here
DEBUG=True
GEMINI_API_KEY=your-gemini-api-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
FFMPEG_PATH=
NODE_PATH=
```

You can create a Gemini API key here:
https://aistudio.google.com

Run migrations:

```powershell
python manage.py migrate
```

Start the backend:

```powershell
python manage.py runserver
```

The API runs at:

```text
http://127.0.0.1:8000/api/
```

## API Routes

| Method | Route | Description | Auth |
| --- | --- | --- | --- |
| POST | `/api/register/` | Create a user account. | No |
| POST | `/api/login/` | Log in and receive JWT cookies. | No |
| POST | `/api/logout/` | Log out and clear JWT cookies. | Yes |
| POST | `/api/token/refresh/` | Refresh the access token from the refresh cookie. | Cookie |
| GET | `/api/quizzes/` | List quizzes owned by the logged-in user. | Yes |
| POST | `/api/quizzes/` | Generate a quiz from a YouTube URL. | Yes |
| GET | `/api/quizzes/{id}/` | Get one quiz with its questions. | Yes |
| PATCH | `/api/quizzes/{id}/` | Update quiz title or description. | Yes |
| DELETE | `/api/quizzes/{id}/` | Delete a quiz. | Yes |

## Example Requests

Register:

```http
POST http://127.0.0.1:8000/api/register/
Content-Type: application/json

{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpassword123",
  "confirmed_password": "testpassword123"
}
```

Login:

```http
POST http://127.0.0.1:8000/api/login/
Content-Type: application/json

{
  "username": "testuser",
  "password": "testpassword123"
}
```

Generate a quiz:

```http
POST http://127.0.0.1:8000/api/quizzes/
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

The login response sets JWT cookies automatically. When testing with Postman or another HTTP client, keep cookies enabled for authenticated requests.

## Frontend

Clone the frontend template separately:

```powershell
git clone https://github.com/Developer-Akademie-Backendkurs/project.Quizly frontend
```

Open it with Live Server in VS Code. The frontend expects the backend at:

```text
http://127.0.0.1:8000
```

## Tests

Run all tests from the backend folder:

```powershell
python manage.py test
```

Run the Django system check:

```powershell
python manage.py check
```

## Notes

- `.env`, `.venv`, `db.sqlite3` and generated media files are ignored by Git.
- The backend stores JWT tokens in HTTP-only cookies.
- Whisper runs locally and does not need an API key.
- Gemini requires `GEMINI_API_KEY` in the `.env` file.
