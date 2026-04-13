import json
import os
import tempfile
from urllib.parse import urlparse

from django.conf import settings


FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")
NODE_PATH = os.getenv("NODE_PATH", "")

if FFMPEG_PATH:
    os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")


def set_auth_cookies(response, refresh):
    """Sets access and refresh tokens as HTTP-only cookies."""
    jwt = settings.SIMPLE_JWT
    httponly = jwt["AUTH_COOKIE_HTTP_ONLY"]
    samesite = jwt["AUTH_COOKIE_SAMESITE"]
    secure = jwt["AUTH_COOKIE_SECURE"]
    access_age = int(jwt["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_age = int(jwt["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        jwt["AUTH_COOKIE"],
        str(refresh.access_token),
        httponly=httponly,
        samesite=samesite,
        secure=secure,
        max_age=access_age,
    )
    response.set_cookie(
        jwt["REFRESH_COOKIE"],
        str(refresh),
        httponly=httponly,
        samesite=samesite,
        secure=secure,
        max_age=refresh_age,
    )


def delete_auth_cookies(response):
    """Deletes the auth cookies from the response."""
    response.delete_cookie(settings.SIMPLE_JWT["AUTH_COOKIE"])
    response.delete_cookie(settings.SIMPLE_JWT["REFRESH_COOKIE"])


def remove_question_timestamps(data):
    """Removes question timestamps from the PATCH response."""
    for question in data["questions"]:
        question.pop("created_at", None)
        question.pop("updated_at", None)
    return data


def is_youtube_url(youtube_url):
    """Checks if the given URL belongs to YouTube."""
    hostname = urlparse(youtube_url).hostname or ""
    allowed_hosts = ["youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"]
    return hostname in allowed_hosts


def get_ydl_options(output_dir):
    """Returns the yt-dlp options for audio downloads."""
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }
    if FFMPEG_PATH:
        options["ffmpeg_location"] = FFMPEG_PATH
    if NODE_PATH:
        options["js_runtimes"] = {"node": {"path": NODE_PATH}}
        options["remote_components"] = ["ejs:github"]
    return options


def download_audio(youtube_url, output_dir):
    """Downloads YouTube audio as a WAV file."""
    import yt_dlp

    ydl_opts = get_ydl_options(output_dir)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    return os.path.join(output_dir, "audio.wav")


def transcribe_audio(audio_path):
    """Transcribes an audio file using Whisper AI."""
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]


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


def generate_quiz_from_transcript(transcript):
    """Sends the transcript to Gemini and returns a list of questions."""
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    prompt = build_quiz_prompt(transcript)
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    questions = json.loads(cleaned)
    if len(questions) != 10:
        raise ValueError("Gemini must return exactly 10 questions.")
    return questions


def process_youtube_url(youtube_url):
    """Full pipeline: downloads audio, transcribes it, and generates a quiz."""
    if not is_youtube_url(youtube_url):
        raise ValueError("Only YouTube URLs are allowed.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)

    questions = generate_quiz_from_transcript(transcript)
    title = f"Quiz - {youtube_url.split('v=')[-1][:11]}"
    description = transcript[:200].strip() + "..."
    return title, description, questions
