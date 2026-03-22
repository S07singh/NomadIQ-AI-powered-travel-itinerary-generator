"""
Structured Output Converter for NomadIQ.

Takes free-form markdown text from agents and converts it into
a strict JSON schema (ItineraryResponse) using the LLM.
"""

import json
import re
from loguru import logger
from config.llm import generate
from models.schemas import ItineraryResponse


def _extract_json(text: str) -> str:
    """
    Robustly extract a JSON object from LLM output that may contain
    extra text, markdown fences, or explanations around the JSON.
    """
    # 1. Remove markdown code fences
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()
    
    # 2. Try to find JSON object by matching outermost { ... }
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                candidate = text[start:i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    start = -1  # try next potential JSON block
    
    # 3. Fallback: try the whole text
    return text.strip()


async def convert_to_structured_json(raw_text: str) -> str:
    """
    Convert free-form agent output into structured ItineraryResponse JSON.
    
    Args:
        raw_text: Combined markdown text from all agents
        
    Returns:
        Valid JSON string matching ItineraryResponse schema
    """
    logger.info("🔄 Converting agent output to structured JSON...")
    
    schema = ItineraryResponse.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    
    prompt = f"""Convert the following travel plan text into a valid JSON object 
matching this exact schema:

{schema_str}

Rules:
- Output ONLY valid JSON, no extra text
- All required fields must be included
- Field types must match schema exactly
- day_by_day_plan should have one entry per day of the trip
- hotels should have the top recommended hotels
- flights should have recommended flights (if mentioned)
- attractions should list all recommended places
- restaurants should list all recommended dining spots
- budget_summary should be a concise cost overview paragraph
- tips should be practical travel tips as a list of strings
- total_estimated_cost should be the total trip cost string

Do NOT wrap the JSON in code blocks. Return raw JSON only.

Text to convert:
{raw_text}"""

    system_instruction = (
        "You are a JSON extraction expert. You read travel planning text and "
        "output strictly valid JSON matching the provided schema. "
        "Never add explanations or markdown formatting. Return only the JSON object."
    )

    try:
        response_text = await generate(
            prompt,
            system_instruction=system_instruction,
            temperature=0.1,
        )
        
        json_string = _extract_json(response_text)
        
        # Validate the JSON parses correctly
        json.loads(json_string)
        logger.info(f"✅ Structured output conversion complete ({len(json_string)} chars)")
        return json_string
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        logger.debug(f"Raw response (first 500 chars): {response_text[:500] if response_text else 'EMPTY'}")
        # Return a minimal valid structure on failure
        fallback = ItineraryResponse(
            tips=["Error converting travel plan to structured format. Raw data was preserved."],
            budget_summary=raw_text[:500],
        )
        return fallback.model_dump_json()
    except Exception as e:
        logger.error(f"❌ Structured output error: {e}")
        fallback = ItineraryResponse(
            tips=[f"Conversion error: {str(e)}"],
        )
        return fallback.model_dump_json()
