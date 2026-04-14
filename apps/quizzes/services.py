import json
import os
import tempfile

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from .models import Question, Quiz
from .utils import is_youtube_url


def process_youtube_url(youtube_url):
    """Full pipeline: downloads audio, transcribes it, and generates a quiz."""
    if not is_youtube_url(youtube_url):
        raise ValueError("Only YouTube URLs are allowed.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)

    questions = generate_quiz_from_transcript(transcript)
    video_id = youtube_url.split("v=")[-1]
    title = f"Quiz - {video_id}"
    description = transcript[:200].strip() + "..."
    return title, description, questions


def download_audio(youtube_url, output_dir):
    """Downloads YouTube audio as a WAV file."""
    import yt_dlp

    ydl_opts = get_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return os.path.join(output_dir, "audio.wav")


def get_ydl_options(output_dir):
    """Returns the yt-dlp options for audio downloads."""
    return {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "postprocessors": [get_audio_postprocessor()],
        "quiet": True,
        "no_warnings": True,
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

    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]


def generate_quiz_from_transcript(transcript):
    """Sends the transcript to Gemini and returns a list of questions."""
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = build_quiz_prompt(transcript)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw_text = response.text.strip()
    cleaned = raw_text.replace("```json", "")
    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.strip()
    questions = json.loads(cleaned)
    if len(questions) != 10:
        raise ValueError("Gemini must return exactly 10 questions.")
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
