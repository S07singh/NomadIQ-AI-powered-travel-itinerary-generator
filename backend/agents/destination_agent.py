"""
Destination Explorer Agent for NomadIQ.

Researches attractions, landmarks, and experiences for a given destination.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

DESTINATION_SYSTEM_PROMPT = """You are an expert travel destination researcher. 
Given a destination and traveler preferences, research and recommend attractions, 
landmarks, activities, and experiences.

Your output should be comprehensive, practical, and tailored to the traveler's style.

For each attraction/activity, include:
- Name and brief description
- Location/area within the destination
- Estimated visit duration
- Approximate cost (or "Free")
- Best time to visit
- Why it matches the traveler's preferences

Focus on a mix of:
- Famous landmarks and must-see spots
- Cultural and historical sites
- Nature and outdoor activities
- Local experiences and hidden gems
- Activities matching the traveler's specific interests

Format your response in clean markdown with clear sections."""


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
    
    prompt = f"""Research the travel destination: {destination}

Here are the traveler's full preferences:
{travel_request_md}

Please provide:
1. **Top 10 Attractions & Activities** tailored to these preferences
2. **Local Areas & Neighborhoods** worth exploring
3. **Cultural Tips** and local customs
4. **Best Times to Visit** specific attractions
5. **Transportation Options** within the destination

Make your recommendations specific, practical, and personalized to the traveler's 
style, budget, and interests described above."""

    try:
        result = await generate(prompt, system_instruction=DESTINATION_SYSTEM_PROMPT, temperature=0.7)
        logger.info(f"✅ Destination Agent: Research complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Destination Agent error: {e}")
        return f"Error researching {destination}: {str(e)}"
