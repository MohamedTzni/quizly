import json
import os
import shutil
import uuid

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from .models import Question, Quiz
from .utils import is_youtube_url


YTDLP_RETRIES = 2
YTDLP_SOCKET_TIMEOUT_SECONDS = 20
GEMINI_TIMEOUT_SECONDS = 60


def log_quiz_step(message):
    """Writes progress for long-running quiz generation requests."""
    print(f"[quiz] {message}", flush=True)


def process_youtube_url(youtube_url):
    """Full pipeline: downloads audio, transcribes it, and generates a quiz."""
    if not is_youtube_url(youtube_url):
        raise ValueError("Only YouTube URLs are allowed.")

    log_quiz_step("Starting quiz generation")
    tmp_dir = create_quiz_temp_dir()
    try:
        audio_path, video_title = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    questions = generate_quiz_from_transcript(transcript)
    title = f"Quiz - {video_title}" if video_title else "Quiz"
    description = transcript[:200].strip() + "..."
    return title, description, questions


def create_quiz_temp_dir():
    """Creates a temporary quiz folder inside Django's media directory."""
    tmp_dir = settings.MEDIA_ROOT / "quiz_tmp" / uuid.uuid4().hex
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_dir)


def download_audio(youtube_url, output_dir):
    """Downloads YouTube audio as a WAV file and returns its video title."""
    import yt_dlp

    log_quiz_step("Reading YouTube metadata")
    ydl_opts = get_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        log_quiz_step("Downloading YouTube audio")
        ydl.download([youtube_url])
    video_title = info.get("title", "") if info else ""
    log_quiz_step("YouTube audio downloaded")
    return os.path.join(output_dir, "audio.wav"), video_title


def get_ydl_options(output_dir):
    """Returns the yt-dlp options for audio downloads."""
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "postprocessors": [get_audio_postprocessor()],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "proxy": "",
        "continuedl": False,
        "socket_timeout": YTDLP_SOCKET_TIMEOUT_SECONDS,
        "retries": YTDLP_RETRIES,
        "fragment_retries": YTDLP_RETRIES,
        "extractor_retries": YTDLP_RETRIES,
    }


def get_audio_postprocessor():
    """Returns the yt-dlp audio postprocessor settings."""
    return {
        "key": "FFmpegExtractAudio",
        "preferredcodec": "wav",
        "preferredquality": "192",
    }


def transcribe_audio(audio_path):
    """Transcribes an audio file using Whisper AI."""
    import whisper

    log_quiz_step("Loading Whisper model")
    model = whisper.load_model("base")
    log_quiz_step("Transcribing audio")
    result = model.transcribe(audio_path)
    log_quiz_step("Audio transcribed")
    return result["text"]


def generate_quiz_from_transcript(transcript):
    """Sends the transcript to Gemini and returns a list of questions."""
    from google import genai

    log_quiz_step("Generating questions with Gemini")
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options={"timeout": GEMINI_TIMEOUT_SECONDS * 1000},
    )
    prompt = build_quiz_prompt(transcript)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw_text = response.text.strip()
    cleaned = raw_text.replace("```json", "")
    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.strip()
    questions = json.loads(cleaned)
    if len(questions) != 10:
        raise ValueError("Gemini must return exactly 10 questions.")
    log_quiz_step("Questions generated")
    return questions


def build_quiz_prompt(transcript):
    """Builds the Gemini prompt from the transcript."""
    prompt = f"""You are a quiz generator.
Create exactly 10 questions from the transcript.
Each question must have exactly 4 answer options.
Return only valid JSON without Markdown or explanations.

Format:
[{{"question_title": "...", "question_options": ["A", "B", "C", "D"], "answer": "A"}}]

Transcript:
{transcript[:3000]}"""
    return prompt


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
