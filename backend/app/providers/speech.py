"""
Speech-to-text, and text-to-speech where a provider supports it (Sarvam). Clients fall back
to on-device speech (expo-speech / Web Speech API) when no TTS-capable provider is configured.
"""

import base64
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

    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, str]:
        """Text → (audio bytes, content type). Providers without TTS raise; callers fall back to on-device speech."""
        raise ProviderError(f"The '{self.name}' speech provider doesn't support text-to-speech", code="tts_unsupported")


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


# Bulbul (TTS) only speaks these; Saaras (STT) understands far more but we only need the
# detected language back to pick a TTS voice, so map whatever it returns onto this set.
SARVAM_TTS_LANGUAGES = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"}


def _sarvam_tts_language(language: str | None) -> str:
    if language in SARVAM_TTS_LANGUAGES:
        return language
    base = (language or "en").split("-")[0].lower()
    for code in SARVAM_TTS_LANGUAGES:
        if code.lower().startswith(base):
            return code
    return "en-IN"


class SarvamSpeechProvider(SpeechProvider):
    """Sarvam AI: Saaras for speech-to-text, Bulbul for text-to-speech. Best-in-class for Indian languages + English."""

    name = "sarvam"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        self.http, self.key = http, api_key

    async def transcribe(self, audio: bytes, content_type: str, language: str | None = None) -> Transcript:
        try:
            resp = await self.http.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": self.key},
                data={"language_code": language or "unknown"},
                files={"file": ("audio.webm", audio, content_type or "audio/webm")},
                timeout=30,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Transcription failed: {exc}", code="stt_failed")
        data = resp.json()
        return Transcript(
            text=data.get("transcript", ""),
            language=data.get("language_code") or language,
            confidence=data.get("language_probability"),
        )

    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, str]:
        try:
            resp = await self.http.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": self.key, "Content-Type": "application/json"},
                json={"text": text[:2500], "language_code": _sarvam_tts_language(language)},
                timeout=30,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Speech synthesis failed: {exc}", code="tts_failed")
        audios = resp.json().get("audios") or []
        if not audios:
            raise ProviderError("Speech synthesis returned no audio", code="tts_failed")
        return base64.b64decode(audios[0]), "audio/wav"
