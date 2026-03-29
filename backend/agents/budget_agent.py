"""
Budget Optimizer Agent for NomadIQ.

Analyzes costs and provides budget breakdowns and optimization tips.
Uses the unified LLM provider (Gemini or Ollama).
"""

from config.llm import generate
from loguru import logger

BUDGET_SYSTEM_PROMPT = """You are a travel budget analyst. Calculate trip costs and provide a breakdown by category. Include total cost, per-day cost, and money-saving tips. Use markdown format. Be concise."""


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
    
    # Truncate context to avoid overwhelming local models
    short_context = context[:2000] if len(context) > 2000 else context
    
    prompt = f"""Analyze budget for a trip to {destination}.

Preferences:
{travel_request_md[:800]}

Trip plan:
{short_context}

Provide:
1. **Total Estimated Cost**
2. **Breakdown**: Transport, Accommodation, Food, Activities
3. **Per-Day Cost**
4. **Money-Saving Tips**

Use the traveler's currency. Be concise."""

    try:
        result = await generate(prompt, system_instruction=BUDGET_SYSTEM_PROMPT, temperature=0.3)
        logger.info(f"✅ Budget Agent: Analysis complete ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"❌ Budget Agent error: {e}")
        return f"Error analyzing budget for {destination}: {str(e)}"
