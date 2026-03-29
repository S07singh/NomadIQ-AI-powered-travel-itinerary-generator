"""
Plan Service — The Core Orchestrator for NomadIQ.

Coordinates all AI agents sequentially to generate a complete travel plan:
  1. Destination research
  2. Hotel search
  3. Dining recommendations
  4. Itinerary creation (uses outputs from 1-3)
  5. Budget analysis (uses outputs from 1-4)
  6. Structured JSON conversion
"""

import json
import time
from loguru import logger
from models.schemas import TravelPlanRequest
from services.db_service import update_plan_status, save_plan_output
from agents.destination_agent import run_destination_agent
from agents.hotel_agent import run_hotel_agent
from agents.dining_agent import run_dining_agent
from agents.itinerary_agent import run_itinerary_agent
from agents.budget_agent import run_budget_agent
from agents.structured_output import convert_to_structured_json
from config.llm import generate


def travel_request_to_markdown(data: TravelPlanRequest) -> str:
    """Convert a TravelPlanRequest into a readable markdown prompt."""
    vibes_str = ", ".join(data.vibes) if data.vibes else "Not specified"
    
    lines = [
        f"# 🧳 Travel Plan Request",
        "",
        "## 📍 Trip Overview",
        f"- **Traveler:** {data.name or 'Traveler'}",
        f"- **Route:** {data.starting_location or 'Not specified'} → {data.destination}",
        f"- **Duration:** {data.duration} days",
        f"- **Dates:** {data.travel_dates.start} to {data.travel_dates.end}",
        "",
        "## 👥 Travel Group",
        f"- **Adults:** {data.adults}",
        f"- **Children:** {data.children}",
        f"- **Traveling With:** {data.traveling_with}",
        "",
        "## 💰 Budget & Preferences",
        f"- **Budget per person:** {data.budget} {data.budget_currency} ({'Flexible' if data.budget_flexible else 'Fixed'})",
        f"- **Travel Style:** {data.travel_style}",
        "",
        "## ✨ Trip Preferences",
        f"- **Travel Vibes:** {vibes_str}",
        f"- **Interests:** {data.interests or 'Not specified'}",
        f"- **Additional Notes:** {data.additional_info or 'None'}",
    ]
    return "\n".join(lines)


async def generate_travel_plan(trip_plan_id: str, travel_plan: TravelPlanRequest) -> str:
    """
    Generate a complete travel plan by orchestrating all agents.
    
    Args:
        trip_plan_id: Unique ID for this trip plan
        travel_plan: The user's travel preferences
        
    Returns:
        JSON string of the final structured itinerary
    """
    logger.info(f"🚀 Starting plan generation for: {trip_plan_id}")
    time_start = time.time()
    
    travel_request_md = travel_request_to_markdown(travel_plan)
    destination = travel_plan.destination
    
    try:
        # ─── Step 1: Destination Research ──────────────────────
        await update_plan_status(trip_plan_id, "processing", "Researching destination attractions")
        destination_result = await run_destination_agent(destination, travel_request_md)
        
        # ─── Step 2: Hotel Search ─────────────────────────────
        await update_plan_status(trip_plan_id, "processing", "Searching for hotels")
        hotel_result = await run_hotel_agent(destination, travel_request_md)
        
        # ─── Step 3: Dining Recommendations ───────────────────
        await update_plan_status(trip_plan_id, "processing", "Finding restaurants")
        dining_result = await run_dining_agent(destination, travel_request_md)
        
        # ─── Step 4: Build context for itinerary ──────────────
        combined_context = f"""
## Destination Research:
{destination_result}

## Hotel Recommendations:
{hotel_result}

## Dining Recommendations:
{dining_result}
"""
        
        # ─── Step 5: Create Itinerary ─────────────────────────
        await update_plan_status(trip_plan_id, "processing", "Creating day-by-day itinerary")
        itinerary_result = await run_itinerary_agent(destination, travel_request_md, combined_context)
        
        # ─── Step 6: Budget Analysis ──────────────────────────
        full_context = combined_context + f"\n## Itinerary:\n{itinerary_result}"
        await update_plan_status(trip_plan_id, "processing", "Analyzing budget")
        budget_result = await run_budget_agent(destination, travel_request_md, full_context)
        
        # ─── Step 7: Convert to Structured JSON ──────────────
        await update_plan_status(trip_plan_id, "processing", "Finalizing your travel plan")
        
        structured_json = await convert_to_structured_json(
            destination_text=destination_result,
            hotel_text=hotel_result,
            dining_text=dining_result,
            itinerary_text=itinerary_result,
            budget_text=budget_result,
            num_days=travel_plan.duration,
        )
        
        # ─── Step 8: Build final response and save ───────────
        # Parse structured_json from string to dict (avoid double-encoding)
        try:
            itinerary_data = json.loads(structured_json) if isinstance(structured_json, str) else structured_json
        except (json.JSONDecodeError, TypeError):
            itinerary_data = structured_json
        
        final_response = json.dumps({
            "itinerary": itinerary_data,
            "raw_responses": {
                "destination_agent": destination_result,
                "hotel_agent": hotel_result,
                "dining_agent": dining_result,
                "itinerary_agent": itinerary_result,
                "budget_agent": budget_result,
            }
        }, indent=2)
        
        await save_plan_output(trip_plan_id, final_response)
        await update_plan_status(trip_plan_id, "completed", "Plan generated successfully")
        
        time_end = time.time()
        logger.info(f"✅ Plan generation complete in {time_end - time_start:.1f}s for: {trip_plan_id}")
        
        return final_response
        
    except Exception as e:
        logger.error(f"❌ Plan generation failed for {trip_plan_id}: {e}", exc_info=True)
        await update_plan_status(trip_plan_id, "failed", error=str(e))
        raise


async def modify_itinerary_via_chat(
    trip_plan_id: str,
    user_message: str,
    current_itinerary: str,
) -> str:
    """
    Modify an existing itinerary based on a user's chat message.
    
    This is the "Roam Around"-style feature: users can say things like
    "Make day 2 more adventurous" or "Add nightlife to day 3".
    
    Args:
        trip_plan_id: ID of the trip plan to modify
        user_message: The user's modification request
        current_itinerary: Current itinerary JSON string
        
    Returns:
        Updated itinerary JSON string
    """
    logger.info(f"💬 Chat modification for {trip_plan_id}: {user_message[:100]}")
    
    prompt = f"""You are modifying an existing travel itinerary based on the user's request.

CURRENT ITINERARY (JSON):
{current_itinerary}

USER'S MODIFICATION REQUEST:
"{user_message}"

Instructions:
1. Understand what the user wants to change
2. Modify ONLY the relevant parts of the itinerary
3. Keep everything else the same
4. Return the COMPLETE updated itinerary as valid JSON matching the same schema
5. Return ONLY the JSON, no extra text or markdown formatting

Return the complete modified itinerary JSON:"""

    system_instruction = (
        "You are a travel itinerary editor. You receive a JSON itinerary and a user request, "
        "then return the modified itinerary as valid JSON. Never add explanations. "
        "Return only the JSON object."
    )

    try:
        result = await generate(
            prompt,
            system_instruction=system_instruction,
            temperature=0.3,
        )
        
        # Robust JSON extraction — find outermost { ... } object
        import re
        result = re.sub(r"```(?:json)?\s*\n?", "", result)
        result = re.sub(r"```", "", result)
        result = result.strip()
        
        depth = 0
        start = -1
        extracted = None
        for i, ch in enumerate(result):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = result[start:i + 1]
                    try:
                        json.loads(candidate)
                        extracted = candidate
                        break
                    except json.JSONDecodeError:
                        start = -1
        
        if extracted:
            result = extracted
        
        # Final validation
        json.loads(result)
        
        logger.info(f"✅ Chat modification complete for {trip_plan_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Chat modification error: {e}")
        raise
