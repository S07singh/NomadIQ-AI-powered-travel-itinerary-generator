"""
API Routes for NomadIQ trip planning.

Endpoints:
  POST /api/plan/trigger  — Start async trip plan generation
  GET  /api/plan/{id}     — Get plan status and results
  GET  /api/plans         — List all plans
  POST /api/chat          — Modify itinerary via AI chat
  GET  /api/chat/{id}     — Get chat history for a plan
"""

import asyncio
import uuid
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from models.schemas import (
    TriggerPlanRequest,
    TriggerPlanResponse,
    PlanStatusResponse,
    ChatRequest,
    ChatResponse,
)
from services.db_service import (
    create_trip_plan,
    get_plan_status,
    get_all_plans,
    save_chat_message,
    get_chat_history,
    update_plan_output,
)
from services.plan_service import generate_travel_plan, modify_itinerary_via_chat

router = APIRouter(prefix="/api", tags=["Travel Plan"])


@router.post(
    "/plan/trigger",
    response_model=TriggerPlanResponse,
    summary="Trigger Trip Plan Generation",
)
async def trigger_plan(request: TriggerPlanRequest) -> TriggerPlanResponse:
    """
    Start generating a travel plan in the background.
    Returns immediately with the plan ID for polling.
    """
    try:
        trip_plan_id = request.trip_plan_id or str(uuid.uuid4())
        logger.info(f"📝 Triggering plan generation: {trip_plan_id}")

        # Save the trip plan to the database
        await create_trip_plan(trip_plan_id, request.travel_plan.model_dump())

        # Run plan generation as a background task
        async def _generate():
            try:
                await generate_travel_plan(trip_plan_id, request.travel_plan)
            except Exception as e:
                logger.error(f"Background plan generation failed: {e}")

        asyncio.create_task(_generate())

        return TriggerPlanResponse(
            success=True,
            message="Trip plan generation started",
            trip_plan_id=trip_plan_id,
        )

    except Exception as e:
        logger.error(f"Error triggering plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/plan/{trip_plan_id}",
    response_model=PlanStatusResponse,
    summary="Get Trip Plan Status & Results",
)
async def get_plan(trip_plan_id: str) -> PlanStatusResponse:
    """
    Get the current status and results of a trip plan.
    Frontend should poll this endpoint every 3-5 seconds while status is 'processing'.
    """
    try:
        plan = await get_plan_status(trip_plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip plan not found: {trip_plan_id}",
            )

        return PlanStatusResponse(
            trip_plan_id=trip_plan_id,
            status=plan.get("status", "pending"),
            current_step=plan.get("current_step"),
            itinerary=plan.get("itinerary"),
            error=plan.get("error"),
            created_at=plan.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/plans", summary="List All Trip Plans")
async def list_plans():
    """Get all trip plans with their statuses."""
    try:
        plans = await get_all_plans()
        return {"success": True, "plans": plans}
    except Exception as e:
        logger.error(f"Error listing plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Modify Itinerary via AI Chat",
)
async def chat_modify(request: ChatRequest) -> ChatResponse:
    """
    Send a message to modify an existing itinerary.
    Example: "Add nightlife to day 2" or "Make this trip cheaper"
    """
    try:
        trip_plan_id = request.trip_plan_id
        logger.info(f"💬 Chat request for {trip_plan_id}: {request.message[:100]}")

        # Get current plan
        plan = await get_plan_status(trip_plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip plan not found: {trip_plan_id}",
            )

        if plan.get("status") != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify a plan that hasn't been generated yet",
            )

        current_itinerary_raw = plan.get("itinerary", "{}")

        # The stored itinerary is wrapped: {"itinerary": {...}, "raw_responses": {...}}
        # We need to extract the inner itinerary for the LLM, then re-wrap after modification
        import json as json_mod
        try:
            parsed = json_mod.loads(current_itinerary_raw) if current_itinerary_raw else {}
            inner_itinerary = parsed.get("itinerary", current_itinerary_raw)
            if isinstance(inner_itinerary, str):
                inner_itinerary_str = inner_itinerary
            else:
                inner_itinerary_str = json_mod.dumps(inner_itinerary, indent=2)
        except (json_mod.JSONDecodeError, TypeError):
            inner_itinerary_str = current_itinerary_raw or "{}"
            parsed = {}

        # Save user message
        await save_chat_message(trip_plan_id, "user", request.message)

        # Modify itinerary using AI (only the inner itinerary)
        updated_inner = await modify_itinerary_via_chat(
            trip_plan_id, request.message, inner_itinerary_str
        )

        # Re-wrap into the full structure, preserving raw_responses
        try:
            full_output = {
                "itinerary": json_mod.loads(updated_inner) if isinstance(updated_inner, str) else updated_inner,
                "raw_responses": parsed.get("raw_responses", {}),
            }
            updated_full = json_mod.dumps(full_output, indent=2)
        except (json_mod.JSONDecodeError, TypeError):
            updated_full = updated_inner

        # Save updated itinerary
        await update_plan_output(trip_plan_id, updated_full)

        # Save AI response
        await save_chat_message(
            trip_plan_id, "assistant", f"Itinerary updated based on your request: {request.message}"
        )

        return ChatResponse(
            success=True,
            message="Itinerary updated successfully",
            updated_itinerary=updated_full,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat modification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/chat/{trip_plan_id}", summary="Get Chat History")
async def get_chat(trip_plan_id: str):
    """Get chat history for a specific trip plan."""
    try:
        messages = await get_chat_history(trip_plan_id)
        return {"success": True, "messages": messages}
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
