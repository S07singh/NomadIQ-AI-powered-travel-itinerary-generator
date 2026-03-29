"""
Destination Explorer Agent for NomadIQ.

Researches attractions, landmarks, and experiences for a given destination.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

DESTINATION_SYSTEM_PROMPT = """You are a travel destination researcher. Recommend top attractions, landmarks, and activities for a destination. For each include: name, description, location, cost, visit duration. Use markdown. Be concise."""


async def run_destination_agent(destination: str, travel_request_md: str) -> str:
    """
    Research a destination and return recommended attractions/activities.
    
    Args:
        destination: The travel destination
        travel_request_md: Full travel request in markdown format
        
    Returns:
        Markdown string with destination research results
    """
    logger.info(f"🏛️ Destination Agent: Researching {destination}")
    
    prompt = f"""Recommend top attractions and activities in {destination}.

Traveler preferences:
{travel_request_md[:800]}

List 5-8 top attractions with: name, description, location, cost, visit duration.
Include landmarks, cultural sites, nature spots, and hidden gems.
Use markdown. Be concise."""

    try:
        result = await generate(prompt, system_instruction=DESTINATION_SYSTEM_PROMPT, temperature=0.7)
        logger.info(f"✅ Destination Agent: Research complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Destination Agent error: {e}")
        return f"Error researching {destination}: {str(e)}"
