"""
Itinerary Specialist Agent for NomadIQ.

Creates detailed day-by-day travel itineraries with hour-by-hour scheduling.
Uses Google Gemini directly (free).
"""

from config.llm import client, get_model_id
from loguru import logger

ITINERARY_SYSTEM_PROMPT = """You are a master itinerary creator with expertise in crafting 
detailed, perfectly-timed daily travel plans.

Given all the travel context (destination research, hotels, restaurants, traveler preferences), 
create a structured day-by-day itinerary.

For each day, organize into three time blocks:
- **Morning (7 AM - 12 PM)**: Breakfast + morning activities
- **Afternoon (12 PM - 6 PM)**: Lunch + main activities
- **Evening (6 PM - 11 PM)**: Dinner + evening activities

For each activity include:
- Specific time (e.g., "9:00 AM - 11:00 AM")
- Activity name and description
- Location
- Estimated cost
- Transport between locations
- Tips for timing

Add daily notes with:
- Weather considerations
- What to wear/bring
- Advance booking reminders
- Local tips

Make the itinerary realistic with proper buffer time between activities.
Format your response in clean markdown with clear sections."""


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
    
    prompt = f"""Create a detailed day-by-day itinerary for a trip to {destination}.

Traveler's preferences:
{travel_request_md}

Available information from research:
{context}

Create a complete itinerary that:
1. Covers every day of the trip with morning/afternoon/evening blocks
2. Includes specific times for each activity
3. References the researched attractions, hotels, and restaurants
4. Accounts for travel time between locations
5. Matches the traveler's pace preference
6. Includes practical daily notes (what to bring, weather tips)
7. Balances activity with rest time

Format each day clearly with time blocks and practical information."""

    try:
        response = await client.aio.models.generate_content(
            model=get_model_id(),
            contents=prompt,
            config={
                "system_instruction": ITINERARY_SYSTEM_PROMPT,
                "temperature": 0.5,
            },
        )
        result = response.text
        logger.info(f"✅ Itinerary Agent: Itinerary created ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Itinerary Agent error: {e}")
        return f"Error creating itinerary for {destination}: {str(e)}"
