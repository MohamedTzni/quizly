import json
import os
import tempfile

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from .models import Question, Quiz
from .utils import is_youtube_url


# ── Whisper model cache ────────────────────────────────────────────────────────
# Loaded once on first use so every quiz request reuses the same in-memory model.
_whisper_model = None

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")
NODE_PATH = os.getenv("NODE_PATH", "")

if FFMPEG_PATH:
    os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")


# ── Generation pipeline ────────────────────────────────────────────────────────

def process_youtube_url(youtube_url):
    """Full pipeline: downloads audio, transcribes it, and generates a quiz."""
    if not is_youtube_url(youtube_url):
        raise ValueError("Only YouTube URLs are allowed.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path, video_title = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)

    questions = generate_quiz_from_transcript(transcript)
    title = f"Quiz - {video_title}" if video_title else f"Quiz - {youtube_url.split('v=')[-1]}"
    description = transcript[:200].strip() + "..."
    return title, description, questions


def download_audio(youtube_url, output_dir):
    """Downloads YouTube audio as a WAV file and returns the path and video title."""
    import yt_dlp

    ydl_opts = get_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        video_title = info.get("title", "") if info else ""
    return os.path.join(output_dir, "audio.wav"), video_title


def get_ydl_options(output_dir):
    """Returns the yt-dlp options for audio downloads."""
    options = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "postprocessors": [get_audio_postprocessor()],
        "quiet": True,
        "no_warnings": True,
    }
    add_optional_ydl_paths(options)
    return options


def get_audio_postprocessor():
    """Returns the yt-dlp audio postprocessor settings."""
    return {
        "key": "FFmpegExtractAudio",
        "preferredcodec": "wav",
        "preferredquality": "192",
    }


def add_optional_ydl_paths(options):
    """Adds optional FFmpeg and Node paths to yt-dlp options."""
    if FFMPEG_PATH:
        options["ffmpeg_location"] = FFMPEG_PATH
    if NODE_PATH:
        options["js_runtimes"] = {"node": {"path": NODE_PATH}}
        options["remote_components"] = ["ejs:github"]


def transcribe_audio(audio_path):
    """Transcribes an audio file using Whisper AI. The model is loaded once and reused."""
    global _whisper_model
    import whisper

    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    result = _whisper_model.transcribe(audio_path)
    return result["text"]


def generate_quiz_from_transcript(transcript):
    """Sends the transcript to Gemini and returns a list of questions.

    Retries up to 3 times with exponential backoff when the API returns 503.
    """
    import time
    from google import genai
    from google.genai import errors as genai_errors

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = build_quiz_prompt(transcript)

    delays = [5, 10, 20]
    for attempt, delay in enumerate(delays, start=1):
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            break
        except genai_errors.ServerError:
            if attempt == len(delays):
                raise
            time.sleep(delay)

    raw_text = response.text.strip()
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    questions = json.loads(cleaned)
    if len(questions) != 10:
        raise ValueError("Gemini must return exactly 10 questions.")
    return questions


def build_quiz_prompt(transcript):
    """Builds the Gemini prompt from the transcript."""
    return f"""You are a quiz generator.
Create exactly 10 questions from the transcript.
Each question must have exactly 4 answer options.
Return only valid JSON without Markdown or explanations.

Format:
[{{"question_title": "...", "question_options": ["A", "B", "C", "D"], "answer": "A"}}]

Transcript:
{transcript[:3000]}"""


# ── Database services ──────────────────────────────────────────────────────────

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
