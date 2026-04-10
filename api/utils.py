"""
Hilfsfunktionen für Quizly:
- YouTube-Audio herunterladen (yt_dlp)
- Audio transkribieren (Whisper AI)
- Quiz aus Transkript generieren (Gemini Flash)
"""

import os
import json
import re
import tempfile
from django.conf import settings


def download_audio(youtube_url: str, output_dir: str) -> str:
    """
    Lädt den Ton eines YouTube-Videos als WAV-Datei herunter.

    Args:
        youtube_url: Vollständige YouTube-URL.
        output_dir: Verzeichnis, in dem die Datei gespeichert wird.

    Returns:
        Absoluter Pfad zur gespeicherten WAV-Datei.
    """
    import yt_dlp
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    ydl_opts = {
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
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    wav_path = os.path.join(output_dir, "audio.wav")
    return wav_path


def transcribe_audio(audio_path: str) -> str:
    """
    Transkribiert eine Audiodatei mit OpenAI Whisper (lokal).

    Args:
        audio_path: Pfad zur Audiodatei.

    Returns:
        Transkribierter Text.
    """
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]


def build_quiz_prompt(transcript: str) -> str:
    """
    Erstellt den Gemini-Prompt aus dem Transkript.

    Args:
        transcript: Transkribierter Videoinhalt.

    Returns:
        Fertiger Prompt-String für Gemini.
    """
    return f"""
Du bist ein Quiz-Generator. Erstelle auf Basis des folgenden Transkripts ein Quiz mit
genau 10 Fragen. Jede Frage hat genau 4 Antwortmöglichkeiten (A, B, C, D).
Gib nur ein valides JSON-Array zurück – kein Markdown, keine Erklärungen.

Format:
[
  {{
    "question_title": "Frage hier",
    "question_options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": "Option A"
  }}
]

Transkript:
{transcript[:8000]}
"""


def generate_quiz_from_transcript(transcript: str) -> list:
    """
    Generiert 10 Quizfragen aus einem Transkript über Gemini Flash.

    Args:
        transcript: Transkribierter Text des Videos.

    Returns:
        Liste mit Fragen-Dictionaries (question_title, question_options, answer).
    """
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = build_quiz_prompt(transcript)
    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    cleaned = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`")
    questions = json.loads(cleaned)
    return questions


def process_youtube_url(youtube_url: str) -> tuple:
    """
    Kompletter Pipeline-Schritt: Download → Transkription → Quiz-Generierung.

    Args:
        youtube_url: YouTube-URL des Videos.

    Returns:
        Tuple (title, description, questions_list)
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)

    questions = generate_quiz_from_transcript(transcript)
    title = f"Quiz – {youtube_url.split('v=')[-1][:11]}"
    description = transcript[:200].strip() + "..."
    return title, description, questions