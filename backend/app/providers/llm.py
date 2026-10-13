"""
LLM providers. All structured generation goes through `generate_json`, which asks
the model for JSON matching a Pydantic schema and validates it — no second
"convert markdown to JSON" pass (that doubled latency in v1).
"""

import json
import re
from abc import ABC, abstractmethod
from typing import TypeVar

import httpx
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.core.exceptions import ProviderError

M = TypeVar("M", bound=BaseModel)


def extract_json(text: str) -> str:
    """Pull the first valid JSON object/array out of model output (handles fences and chatter)."""
    if not text:
        return "{}"
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        depth, start = 0, -1
        for i, ch in enumerate(text):
            if ch == open_ch:
                if depth == 0:
                    start = i
                depth += 1
            elif ch == close_ch and depth:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start : i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        start = -1
    return text


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str: ...

    @abstractmethod
    async def _generate_json_text(self, prompt: str, system: str, schema: dict, temperature: float) -> str: ...

    async def generate_json(
        self,
        prompt: str,
        schema: type[M],
        system: str = "",
        temperature: float = 0.3,
        retries: int = 1,
    ) -> M:
        json_schema = schema.model_json_schema()
        full_system = (
            f"{system}\n\nRespond ONLY with a single JSON object that validates against this JSON schema. "
            f"No markdown, no commentary.\nSCHEMA: {json.dumps(json_schema, separators=(',', ':'))}"
        ).strip()
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            text = await self._generate_json_text(prompt, full_system, json_schema, temperature)
            try:
                return schema.model_validate(json.loads(extract_json(text)))
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(f"LLM JSON for {schema.__name__} invalid (attempt {attempt + 1}): {str(exc)[:200]}")
        raise ProviderError(f"AI returned invalid {schema.__name__}", code="llm_invalid_output", details=str(last_error)[:500])


class MockLLM(LLMProvider):
    """Deterministic offline LLM. Schemas may define `mock_example(prompt)` to return realistic data."""

    name = "mock"

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        return f"[mock] {prompt[:200]}"

    async def _generate_json_text(self, prompt: str, system: str, schema: dict, temperature: float) -> str:
        return "{}"

    async def generate_json(self, prompt, schema, system="", temperature=0.3, retries=1):
        factory = getattr(schema, "mock_example", None)
        if callable(factory):
            return factory(prompt)
        return schema.model_validate({})


class OllamaLLM(LLMProvider):
    name = "ollama"

    def __init__(self, http: httpx.AsyncClient, base_url: str, model: str, timeout: float):
        self.http, self.base_url, self.model, self.timeout = http, base_url.rstrip("/"), model, timeout

    async def _chat(self, prompt: str, system: str, temperature: float, fmt: dict | None) -> str:
        body: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if fmt is not None:
            body["format"] = fmt  # Ollama structured outputs: constrain to JSON schema
        try:
            resp = await self.http.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}", code="llm_unavailable")
        return resp.json().get("message", {}).get("content", "")

    async def generate(self, prompt, system="", temperature=0.7):
        return await self._chat(prompt, system, temperature, None)

    async def _generate_json_text(self, prompt, system, schema, temperature):
        return await self._chat(prompt, system, temperature, schema)


class GeminiLLM(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install google-genai to use LLM_PROVIDER=gemini") from exc
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def _call(self, prompt: str, system: str, temperature: float, json_mode: bool) -> str:
        config: dict = {"system_instruction": system or None, "temperature": temperature}
        if json_mode:
            config["response_mime_type"] = "application/json"
        try:
            resp = await self.client.aio.models.generate_content(model=self.model, contents=prompt, config=config)
        except Exception as exc:
            code = "llm_rate_limited" if "429" in str(exc) else "llm_unavailable"
            raise ProviderError(f"Gemini request failed: {exc}", code=code)
        return resp.text or ""

    async def generate(self, prompt, system="", temperature=0.7):
        return await self._call(prompt, system, temperature, False)

    async def _generate_json_text(self, prompt, system, schema, temperature):
        return await self._call(prompt, system, temperature, True)
