"""
Speech-to-text. Text-to-speech is done on-device (expo-speech / Web Speech API)
for zero added latency, so the backend only transcribes.
"""

from abc import ABC, abstractmethod

import httpx

from app.common.schemas import APIModel
from app.core.exceptions import ProviderError

DEFAULT_MOCK_TRANSCRIPT = "Plan a 3 day trip to Goa"


class Transcript(APIModel):
    text: str
    language: str | None = None
    confidence: float | None = None
    duration_seconds: float | None = None


class SpeechProvider(ABC):
    name = "base"

    @abstractmethod
    async def transcribe(self, audio: bytes, content_type: str, language: str | None = None) -> Transcript: ...


class MockSpeechProvider(SpeechProvider):
    """If the 'audio' is UTF-8 text (handy in tests and demos) it is returned as the transcript."""

    name = "mock"

    async def transcribe(self, audio: bytes, content_type: str, language: str | None = None) -> Transcript:
        try:
            text = audio.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = ""
        if not text or not text.isprintable():
            text = DEFAULT_MOCK_TRANSCRIPT
        return Transcript(text=text, language=language or "en", confidence=0.99, duration_seconds=2.0)


class DeepgramSpeechProvider(SpeechProvider):
    """Deepgram Nova-3: low latency and cheap; supports Hindi/English code-switching."""

    name = "deepgram"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        self.http, self.key = http, api_key

    async def transcribe(self, audio: bytes, content_type: str, language: str | None = None) -> Transcript:
        params = {"model": "nova-3", "smart_format": "true"}
        if language:
            params["language"] = language
        else:
            params["detect_language"] = "true"
        try:
            resp = await self.http.post(
                "https://api.deepgram.com/v1/listen",
                params=params,
                content=audio,
                headers={"Authorization": f"Token {self.key}", "Content-Type": content_type or "audio/webm"},
                timeout=60,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Transcription failed: {exc}", code="stt_failed")
        data = resp.json()
        channel = data["results"]["channels"][0]
        alt = channel["alternatives"][0]
        return Transcript(
            text=alt.get("transcript", ""),
            language=channel.get("detected_language") or language,
            confidence=alt.get("confidence"),
            duration_seconds=(data.get("metadata") or {}).get("duration"),
        )


class OpenAISpeechProvider(SpeechProvider):
    name = "openai"

    def __init__(self, http: httpx.AsyncClient, api_key: str, model: str = "gpt-4o-mini-transcribe"):
        self.http, self.key, self.model = http, api_key, model

    async def transcribe(self, audio: bytes, content_type: str, language: str | None = None) -> Transcript:
        data = {"model": self.model}
        if language:
            data["language"] = language
        try:
            resp = await self.http.post(
                "https://api.openai.com/v1/audio/transcriptions",
                data=data,
                files={"file": ("audio", audio, content_type or "audio/webm")},
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=60,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Transcription failed: {exc}", code="stt_failed")
        return Transcript(text=resp.json().get("text", ""), language=language)
