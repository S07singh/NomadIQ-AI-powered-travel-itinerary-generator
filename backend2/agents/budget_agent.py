"""
Budget Optimizer Agent for NomadIQ.

Analyzes costs and provides budget breakdowns and optimization tips.
Uses Google Gemini directly (free).
"""

from config.llm import client, get_model_id
from loguru import logger

BUDGET_SYSTEM_PROMPT = """You are a travel budget expert and financial planner.
Given a complete travel plan with hotels, activities, and dining, calculate 
the total estimated cost and provide a detailed budget breakdown.

Your analysis should include:
- Itemized cost breakdown by category (accommodation, food, activities, transport)
- Total estimated trip cost
- Per-person and per-day costs
- Money-saving alternatives where applicable
- Hidden costs to watch out for
- Tipping customs
- Currency exchange tips

All amounts should be in the traveler's preferred currency.
If costs exceed the stated budget, suggest specific alternatives to reduce costs.
If costs are well under budget, suggest premium upgrades they could afford.

Format your response in clean markdown with clear sections and tables."""


async def run_budget_agent(
    destination: str,
    travel_request_md: str,
    context: str,
) -> str:
    """
    Analyze costs and optimize the travel budget.
    
    Args:
        destination: The travel destination
        travel_request_md: Full travel request in markdown format
        context: Combined output from all other agents
        
    Returns:
        Markdown string with budget analysis and recommendations
    """
    logger.info(f"💰 Budget Agent: Analyzing costs for {destination}")
    
    prompt = f"""Analyze and optimize the budget for a trip to {destination}.

Traveler's preferences and budget:
{travel_request_md}

Complete trip plan so far:
{context}

Please provide:
1. **Total Estimated Cost** for the entire trip
2. **Breakdown by Category**:
   - ✈️ Transportation (flights, local transport)
   - 🏨 Accommodation (total for all nights)
   - 🍽️ Food & Dining (daily estimates)
   - 🎯 Activities & Attractions (entrance fees, tours)
   - 🛍️ Shopping & Miscellaneous
   - 📱 Connectivity (SIM cards, WiFi)
3. **Per-Person Cost** and **Per-Day Cost**
4. **Budget vs. Actual** comparison
5. **Money-Saving Tips** specific to this destination
6. **Hidden Costs** to watch out for
7. **Currency & Payment Tips**

Use the traveler's stated currency for all amounts."""

    try:
        response = await client.aio.models.generate_content(
            model=get_model_id(),
            contents=prompt,
            config={
                "system_instruction": BUDGET_SYSTEM_PROMPT,
                "temperature": 0.3,
            },
        )
        result = response.text
        logger.info(f"✅ Budget Agent: Analysis complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Budget Agent error: {e}")
        return f"Error analyzing budget for {destination}: {str(e)}"
