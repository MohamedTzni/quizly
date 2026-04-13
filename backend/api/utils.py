import os
import json
import tempfile
from django.conf import settings

FFMPEG_PATH = "C:/Users/moham/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin"
os.environ["PATH"] = FFMPEG_PATH + os.pathsep + os.environ.get("PATH", "")


def download_audio(youtube_url, output_dir):
    """Downloads YouTube audio as a WAV file."""
    import yt_dlp
    output_template = os.path.join(output_dir, "audio.%(ext)s")
    ffmpeg_path = "C:/Users/moham/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin"
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}],
        "quiet": True,
        "no_warnings": True,
        "js_runtimes": {"node": {"path": "C:/Program Files/nodejs/node.exe"}},
        "remote_components": ["ejs:github"],
        "ffmpeg_location": ffmpeg_path,
    }
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
    prompt = f"""Du bist ein Quiz-Generator. Erstelle auf Basis des folgenden Transkripts ein Quiz mit genau 10 Fragen. Jede Frage hat genau 4 Antwortmöglichkeiten (A, B, C, D). Gib nur ein valides JSON-Array zurück – kein Markdown, keine Erklärungen.

Format:
[{{"question_title": "...", "question_options": ["A", "B", "C", "D"], "answer": "A"}}]

Transkript:
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
    return questions


def process_youtube_url(youtube_url):
    """Full pipeline: downloads audio, transcribes it, and generates a quiz."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = download_audio(youtube_url, tmp_dir)
        transcript = transcribe_audio(audio_path)
    questions = generate_quiz_from_transcript(transcript)
    title = f"Quiz – {youtube_url.split('v=')[-1][:11]}"
    description = transcript[:200].strip() + "..."
    return title, description, questions
