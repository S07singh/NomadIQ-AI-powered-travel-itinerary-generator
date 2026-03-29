"""
Structured Output Converter for NomadIQ.

Uses per-section micro-conversions instead of one massive LLM call.
Each agent's text is independently converted to a small JSON snippet,
then assembled into the final ItineraryResponse.

This approach works reliably with local models (Ollama) because each
conversion prompt is small (~2K chars instead of ~17K).
"""

import json
import re
from loguru import logger
from config.llm import generate
from models.schemas import ItineraryResponse


def _extract_json(text: str) -> str:
    """
    Robustly extract a JSON object/array from LLM output that may contain
    extra text, markdown fences, or explanations around the JSON.
    """
    if not text:
        return "{}"
    
    # 1. Remove markdown code fences
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()
    
    # 2. Try to find JSON by matching outermost { ... } or [ ... ]
    for open_ch, close_ch in [('{', '}'), ('[', ']')]:
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == open_ch:
                if depth == 0:
                    start = i
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = text[start:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        start = -1
    
    # 3. Fallback
    return text.strip()


async def _convert_section(raw_text: str, section_name: str, json_template: str) -> str:
    """
    Convert a single agent section to JSON using a small, focused prompt.
    Falls back to empty on failure.
    """
    prompt = f"""Extract data from this travel text and return ONLY a valid JSON {json_template}

TEXT:
{raw_text[:4000]}

RULES:
- Return ONLY raw JSON, no explanations, no markdown
- If a field is unknown, use empty string ""
- Match the exact template structure above"""

    system_instruction = "You output only valid JSON. Never add explanations or markdown."
    
    try:
        response = await generate(
            prompt,
            system_instruction=system_instruction,
            temperature=0.1,
        )
        
        if not response or not response.strip():
            logger.warning(f"⚠️ Empty response for {section_name}, using fallback")
            return "[]" if json_template.startswith("array") else "{}"
        
        extracted = _extract_json(response)
        # Validate
        json.loads(extracted)
        logger.info(f"✅ {section_name}: converted ({len(extracted)} chars)")
        return extracted
    except Exception as e:
        logger.error(f"❌ {section_name} conversion failed: {e}")
        return "[]" if json_template.startswith("array") else "{}"


async def convert_to_structured_json(
    destination_text: str,
    hotel_text: str,
    dining_text: str,
    itinerary_text: str,
    budget_text: str,
    num_days: int = 3,
) -> str:
    """
    Convert agent outputs into structured ItineraryResponse JSON.
    Does 5 small per-section conversions instead of one massive call.
    """
    logger.info("🔄 Converting agent outputs to structured JSON (per-section)...")
    
    # ── 1. Attractions from destination agent ──
    attractions_json = await _convert_section(
        destination_text,
        "Attractions",
        f"""array of objects, each with keys: "name", "description", "location", "estimated_cost", "visit_duration". Example:
[{{"name": "Eiffel Tower", "description": "Iconic iron tower", "location": "Champ de Mars", "estimated_cost": "$30", "visit_duration": "2 hours"}}]"""
    )
    
    # ── 2. Hotels ──
    hotels_json = await _convert_section(
        hotel_text,
        "Hotels",
        f"""array of objects, each with keys: "hotel_name", "price", "rating", "location", "amenities", "description". Example:
[{{"hotel_name": "Grand Hotel", "price": "$150/night", "rating": "4.5", "location": "Downtown", "amenities": "WiFi, Pool, Restaurant", "description": "Luxury downtown hotel"}}]"""
    )
    
    # ── 3. Restaurants ──
    restaurants_json = await _convert_section(
        dining_text,
        "Restaurants",
        f"""array of objects, each with keys: "name", "cuisine", "price_range", "description", "location". Example:
[{{"name": "Le Bistro", "cuisine": "French", "price_range": "$$", "description": "Cozy French cafe", "location": "Downtown"}}]"""
    )
    
    # ── 4. Day-by-day itinerary ──
    itinerary_json = await _convert_section(
        itinerary_text,
        "Itinerary",
        f"""array of EXACTLY {num_days} objects (one per day). Keys: "day", "date", "morning", "afternoon", "evening", "notes".
You MUST include ALL {num_days} days, not just Day 1. Example for a 2-day trip:
[{{"day": 1, "date": "Day 1", "morning": "Visit temple", "afternoon": "Lunch and explore market", "evening": "Dinner at restaurant", "notes": "Wear comfortable shoes"}},
 {{"day": 2, "date": "Day 2", "morning": "Hike to waterfall", "afternoon": "Visit museum", "evening": "Local dinner", "notes": "Bring rain jacket"}}]"""
    )
    
    # ── 5. Budget summary (just extract key text, no JSON conversion needed) ──
    budget_summary = budget_text[:1000] if budget_text else "No budget data available"
    # Try to extract a total cost
    total_cost = ""
    cost_patterns = [
        r'total[:\s]*[\$₹€£]\s*[\d,]+(?:\.\d{2})?',
        r'[\$₹€£]\s*[\d,]+(?:\.\d{2})?\s*(?:total|overall)',
        r'estimated total[:\s]*[\$₹€£]?\s*[\d,]+',
        r'total (?:estimated )?(?:cost|budget)[:\s]*[\$₹€£]?\s*[\d,]+',
    ]
    for pattern in cost_patterns:
        match = re.search(pattern, budget_text, re.IGNORECASE)
        if match:
            total_cost = match.group(0).strip()
            break
    
    # Helper: if LLM returned {"key": [...]} instead of [...], extract the list
    def _ensure_list(val):
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                return []
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            # Look for a nested list of DICTS (structured data), not strings
            for v in val.values():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    return v
            # No list of dicts found — wrap the dict itself as a single item
            if val:
                return [val]
        return []
    
    attractions = _ensure_list(attractions_json)
    hotels = _ensure_list(hotels_json)
    restaurants = _ensure_list(restaurants_json)
    itinerary = _ensure_list(itinerary_json)
    
    logger.info(f"📊 Extracted: {len(attractions)} attractions, {len(hotels)} hotels, {len(restaurants)} restaurants, {len(itinerary)} day plans")

    result = {
        "day_by_day_plan": itinerary,
        "hotels": hotels,
        "flights": [],
        "attractions": attractions,
        "restaurants": restaurants,
        "budget_summary": budget_summary,
        "tips": [],
        "total_estimated_cost": total_cost,
    }
    
    result_json = json.dumps(result, indent=2)
    logger.info(f"✅ Structured output assembly complete ({len(result_json)} chars)")
    return result_json
