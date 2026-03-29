"""
Itinerary Specialist Agent for NomadIQ.

Creates detailed day-by-day travel itineraries with hour-by-hour scheduling.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

ITINERARY_SYSTEM_PROMPT = """You are a travel itinerary planner. Create concise day-by-day plans with morning, afternoon, and evening activities. Use markdown format. Be brief and practical."""


async def run_itinerary_agent(
    destination: str,
    travel_request_md: str,
    context: str,
) -> str:
    """
    Create a detailed day-by-day itinerary.
    
    Args:
        destination: The travel destination
        travel_request_md: Full travel request in markdown format
        context: Combined output from other agents (attractions, hotels, restaurants)
        
    Returns:
        Markdown string with the day-by-day itinerary
    """
    logger.info(f"📅 Itinerary Agent: Creating itinerary for {destination}")
    
    # Truncate context to avoid overwhelming local models
    short_context = context[:2000] if len(context) > 2000 else context
    
    prompt = f"""Create a {destination} trip itinerary.

Preferences:
{travel_request_md[:800]}

Context:
{short_context}

For each day write:
- **Morning**: activities
- **Afternoon**: activities  
- **Evening**: activities
- **Notes**: tips

Keep it concise. Use markdown."""

    try:
        result = await generate(prompt, system_instruction=ITINERARY_SYSTEM_PROMPT, temperature=0.5)
        logger.info(f"✅ Itinerary Agent: Itinerary created ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Itinerary Agent error: {e}")
        return f"Error creating itinerary for {destination}: {str(e)}"
