"""
Hotel Search Agent for NomadIQ.

Recommends accommodations based on destination, budget, and travel style.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

HOTEL_SYSTEM_PROMPT = """You are a hotel search assistant. Recommend hotels with: name, price per night, rating, location, amenities, description. Provide 3-5 options across different price points. Use markdown. Be concise."""


async def run_hotel_agent(destination: str, travel_request_md: str) -> str:
    """
    Search for hotel recommendations for a destination.
    
    Args:
        destination: The travel destination
        travel_request_md: Full travel request in markdown format
        
    Returns:
        Markdown string with hotel recommendations
    """
    logger.info(f"🏨 Hotel Agent: Searching hotels in {destination}")
    
    prompt = f"""Recommend hotels in {destination}.

Preferences:
{travel_request_md[:800]}

List 3-5 hotels with: name, price/night, rating, location, amenities, description.
Use markdown. Be concise."""

    try:
        result = await generate(prompt, system_instruction=HOTEL_SYSTEM_PROMPT, temperature=0.5)
        logger.info(f"✅ Hotel Agent: Search complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Hotel Agent error: {e}")
        return f"Error searching hotels in {destination}: {str(e)}"
