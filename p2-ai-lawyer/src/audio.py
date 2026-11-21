"""Audio transcription using Groq Whisper and optional spoken replies via gTTS."""

import io
import os
from typing import Optional

from gtts import gTTS

try:
    from groq import Groq
except ImportError:
    Groq = None


def transcribe_audio(audio_bytes: bytes, filename: str = "input.wav") -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Audio transcription unavailable: GROQ_API_KEY not configured in .env."
    if not Groq:
        return "Audio transcription unavailable: groq SDK not installed."

    client = Groq(api_key=api_key)
    file_tuple = (filename, io.BytesIO(audio_bytes))
    transcription = client.audio.transcriptions.create(
        file=file_tuple,
        model="whisper-large-v3",
    )
    return str(transcription.text)


def synthesize_speech(text: str, output_path: str = "/tmp/speech.mp3", lang_code: str = "en") -> Optional[str]:
    clean_text = text.replace("*", "").replace("#", "").strip()[:500]
    if not clean_text:
        return None
    tts_lang = "hi" if lang_code == "hindi" else "en"
    tts = gTTS(text=clean_text, lang=tts_lang, slow=False)
    tts.save(output_path)
    return output_path
