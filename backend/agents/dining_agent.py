"""
Dining Agent for NomadIQ.

Recommends restaurants, food markets, and culinary experiences.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

DINING_SYSTEM_PROMPT = """You are a food guide. Recommend restaurants with: name, cuisine, price range, description, location. Include 3-5 restaurants and local food tips. Use markdown. Be concise."""


async def run_dining_agent(destination: str, travel_request_md: str) -> str:
    """
    Find restaurant and dining recommendations for a destination.
    
    Args:
        destination: The travel destination
        travel_request_md: Full travel request in markdown format
        
    Returns:
        Markdown string with dining recommendations
    """
    logger.info(f"🍽️ Dining Agent: Finding restaurants in {destination}")
    
    prompt = f"""Recommend restaurants and food in {destination}.

Preferences:
{travel_request_md[:800]}

List 3-5 restaurants with: name, cuisine, price range, description, location.
Mention local specialties and street food. Use markdown. Be concise."""

    try:
        result = await generate(prompt, system_instruction=DINING_SYSTEM_PROMPT, temperature=0.7)
        logger.info(f"✅ Dining Agent: Search complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Dining Agent error: {e}")
        return f"Error finding restaurants in {destination}: {str(e)}"
