# Quizly Backend

This project was created as part of the Fullstack Developer training at Developer Akademie.
The frontend was provided and can be found here:
https://github.com/Developer-Akademie-Backendkurs/project.Quizly

This backend creates quizzes from YouTube videos. It downloads the audio, transcribes it with Whisper AI and generates quiz questions with Gemini.

## Requirements

- Python 3
- FFmpeg installed globally
- A Gemini API key
- Optional: Node.js, if `yt-dlp` needs a JavaScript runtime for YouTube

FFmpeg is required because `yt-dlp` and Whisper need it for audio processing.

Windows:

```powershell
winget install --id Gyan.FFmpeg -e --source winget
```

macOS:

```bash
brew install ffmpeg
```

## Setup

Open a terminal in the backend folder:

```powershell
cd backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```env
SECRET_KEY=your-django-secret-key-here
DEBUG=True
GEMINI_API_KEY=your-gemini-api-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
FFMPEG_PATH=
NODE_PATH=
```

`FFMPEG_PATH` and `NODE_PATH` are optional. Use them only if FFmpeg or Node.js are not found automatically.

Run the migrations:

```powershell
python manage.py migrate
```

Start the backend:

```powershell
python manage.py runserver
```

The API is available at:

```text
http://127.0.0.1:8000/api/
```

## Tests

Run the tests with:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Run the Django system check with:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

## Authentication

The backend uses JWT authentication with HTTP-only cookies.

- `access_token` stores the access token.
- `refresh_token` stores the refresh token.
- Tokens are not stored in localStorage.
- Logout blacklists the refresh token and deletes the cookies.

## Quiz Generation

The quiz creation endpoint expects a YouTube URL.

The backend does the following:

1. Checks that the URL belongs to YouTube.
2. Downloads the audio with `yt-dlp`.
3. Converts the audio with FFmpeg.
4. Transcribes the audio with Whisper.
5. Sends the transcript to Gemini.
6. Checks that Gemini returned exactly 10 questions.
7. Saves the quiz and questions in the database.

## Important Notes

- Keep `.env`, `.venv` and `db.sqlite3` out of Git.
- The frontend is not part of this backend repository.
- Legal notice and privacy policy are provided by the frontend template.
