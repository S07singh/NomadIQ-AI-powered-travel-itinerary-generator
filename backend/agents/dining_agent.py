"""
Dining Agent for NomadIQ.

Recommends restaurants, food markets, and culinary experiences.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

DINING_SYSTEM_PROMPT = """You are an expert culinary guide and food critic.
Given a destination and traveler preferences, recommend restaurants, food markets, 
and culinary experiences.

For each restaurant recommendation, include:
- Restaurant name
- Cuisine type
- Price range ($, $$, $$$)
- Location/area
- Must-try dishes
- Ambiance description
- Best for (breakfast/lunch/dinner)

Also recommend:
- Local food markets and street food
- Culinary experiences (cooking classes, food tours)
- Local specialties and must-try dishes

Provide at least 5 restaurant recommendations.
Format your response in clean markdown with clear sections."""


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
    
    prompt = f"""Find the best dining and food experiences in: {destination}

Here are the traveler's full preferences:
{travel_request_md}

Please provide:
1. **Top 5 Restaurant Recommendations** with cuisine, price range, and must-try dishes
2. **Food Markets & Street Food** spots worth visiting
3. **Culinary Experiences** (cooking classes, food tours, tastings)
4. **Local Specialties** - dishes unique to this destination
5. **Dining Tips** - reservation needs, local customs, best dining times

Match recommendations to the traveler's budget and dietary preferences if mentioned."""

    try:
        result = await generate(prompt, system_instruction=DINING_SYSTEM_PROMPT, temperature=0.7)
        logger.info(f"✅ Dining Agent: Search complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Dining Agent error: {e}")
        return f"Error finding restaurants in {destination}: {str(e)}"
