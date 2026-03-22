"""
LLM Configuration for NomadIQ.

Supports two providers (set LLM_PROVIDER in .env):
  1. "gemini"  — Google Gemini API (free tier, rate-limited)
  2. "ollama"  — Local Ollama (unlimited, no API key needed)

To use Ollama:
  1. Install: https://ollama.com/download
  2. Pull a model: ollama pull llama3.1
  3. Set in .env: LLM_PROVIDER=ollama
"""

import os
import json
import httpx
from loguru import logger

# ─── Configuration ────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # "gemini" or "ollama"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Initialize Gemini client only if needed
_gemini_client = None
if LLM_PROVIDER == "gemini":
    try:
        from google import genai
        _gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        logger.info(f"🤖 LLM Provider: Gemini ({GEMINI_MODEL})")
    except Exception as e:
        logger.warning(f"Gemini init failed: {e}. Falling back to Ollama.")
        LLM_PROVIDER = "ollama"

if LLM_PROVIDER == "ollama":
    logger.info(f"🤖 LLM Provider: Ollama ({OLLAMA_MODEL}) at {OLLAMA_BASE_URL}")


async def generate(
    prompt: str,
    system_instruction: str = "",
    temperature: float = 0.7,
) -> str:
    """
    Unified LLM generation function. Works with both Gemini and Ollama.

    Args:
        prompt: The user/task prompt
        system_instruction: System-level instructions for the model
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

    Returns:
        The generated text response
    """
    if LLM_PROVIDER == "gemini":
        return await _generate_gemini(prompt, system_instruction, temperature)
    else:
        return await _generate_ollama(prompt, system_instruction, temperature)


async def _generate_gemini(prompt: str, system_instruction: str, temperature: float) -> str:
    """Generate using Google Gemini API."""
    try:
        response = await _gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "temperature": temperature,
            },
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.warning("⚠️ Gemini rate limit hit. Consider switching to Ollama (LLM_PROVIDER=ollama)")
        raise


async def _generate_ollama(prompt: str, system_instruction: str, temperature: float) -> str:
    """Generate using local Ollama server."""
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
