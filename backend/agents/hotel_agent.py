"""
Hotel Search Agent for NomadIQ.

Recommends accommodations based on destination, budget, and travel style.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

HOTEL_SYSTEM_PROMPT = """You are an expert hotel and accommodation search assistant.
Given a destination and traveler preferences, recommend the best hotels and stays.

For each hotel recommendation, include:
- Hotel name
- Price range per night (in the traveler's currency)
- Star rating
- Location/area and why it's good
- Key amenities
- Brief description of the stay experience
- Who it's best for (couples, families, solo, etc.)

Provide 5 hotel recommendations spanning different price points within the budget.
Include a mix of:
- Hotels
- Boutique stays
- Budget-friendly options if applicable

Format your response in clean markdown with clear sections."""


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
    
    prompt = f"""Find the best hotel recommendations for: {destination}

Here are the traveler's full preferences:
{travel_request_md}

Please provide:
1. **Top 5 Hotel Recommendations** sorted by best value
2. For each hotel include: name, price per night, rating, location, key amenities, description
3. **Why each hotel matches** the traveler's style and budget
4. **Booking tips** for getting the best rates
5. **Area recommendations** - which neighborhoods are best to stay in

Make sure recommendations fit within the stated budget and travel style."""

    try:
        result = await generate(prompt, system_instruction=HOTEL_SYSTEM_PROMPT, temperature=0.5)
        logger.info(f"✅ Hotel Agent: Search complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Hotel Agent error: {e}")
        return f"Error searching hotels in {destination}: {str(e)}"
