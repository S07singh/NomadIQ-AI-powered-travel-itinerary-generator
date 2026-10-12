import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.common.schemas import Page
from app.core.deps import DB, CurrentUser, JobsDep, PageParams, ProvidersDep, SettingsDep
from app.modules.trips.schemas import (
    ShareResponse,
    TripChatRequest,
    TripChatResponse,
    TripCreate,
    TripMessage,
    TripOut,
    TripProgress,
    TripStatus,
    TripSummary,
    TripUpdate,
)
from app.modules.trips.service import TripService

router = APIRouter(prefix="/trips", tags=["Trips"])
shared_router = APIRouter(prefix="/shared", tags=["Trips"])

SSE_POLL_SECONDS = 1.0
SSE_MAX_SECONDS = 600


def get_service(db: DB, providers: ProvidersDep, settings: SettingsDep, jobs: JobsDep) -> TripService:
    return TripService(db, providers, settings, jobs)


Service = Annotated[TripService, Depends(get_service)]


@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED, summary="Create a trip (and start AI planning)")
async def create_trip(data: TripCreate, user: CurrentUser, service: Service) -> TripOut:
    return await service.create(user, data)


@router.get("", response_model=Page[TripSummary], summary="List my trips")
async def list_trips(
    user: CurrentUser,
    service: Service,
    paging: PageParams,
    status_filter: Annotated[TripStatus | None, Query(alias="status")] = None,
) -> Page[TripSummary]:
    return await service.list_trips(user, status_filter, paging.page, paging.limit)


@router.get("/{trip_id}", response_model=TripOut, summary="Get a trip with its full plan")
async def get_trip(trip_id: str, user: CurrentUser, service: Service) -> TripOut:
    return await service.get(user, trip_id)


@router.patch("/{trip_id}", response_model=TripOut, summary="Edit trip inputs (does not re-plan)")
async def update_trip(trip_id: str, data: TripUpdate, user: CurrentUser, service: Service) -> TripOut:
    return await service.update(user, trip_id, data)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a trip")
async def delete_trip(trip_id: str, user: CurrentUser, service: Service) -> None:
    await service.delete(user, trip_id)


@router.post("/{trip_id}/generate", response_model=TripOut, status_code=status.HTTP_202_ACCEPTED, summary="(Re)generate the AI plan")
async def generate_trip(trip_id: str, user: CurrentUser, service: Service) -> TripOut:
    return await service.regenerate(user, trip_id)


@router.get("/{trip_id}/status", response_model=TripProgress, summary="Lightweight generation progress (for polling)")
async def trip_status(trip_id: str, user: CurrentUser, service: Service) -> TripProgress:
    return await service.progress(user, trip_id)


@router.get(
    "/{trip_id}/events",
    summary="Server-Sent Events stream of generation progress",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}, "description": "`progress` events then a final `done` event"}},
)
async def trip_events(trip_id: str, request: Request, user: CurrentUser, service: Service) -> StreamingResponse:
    await service.get_doc(user, trip_id, {"_id": 1})  # 404 before opening the stream

    async def stream():
        last = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + SSE_MAX_SECONDS
        while loop.time() < deadline:
            if await request.is_disconnected():
                return
            progress = await service.progress(user, trip_id)
            payload = progress.model_dump(mode="json")
            if payload != last:
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                last = payload
            if progress.status in (TripStatus.ready, TripStatus.failed, TripStatus.draft):
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                return
            await asyncio.sleep(SSE_POLL_SECONDS)
        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{trip_id}/chat", response_model=TripChatResponse, summary="Ask about or modify the itinerary in natural language")
async def chat(trip_id: str, data: TripChatRequest, user: CurrentUser, service: Service) -> TripChatResponse:
    return await service.chat(user, trip_id, data.message)


@router.get("/{trip_id}/chat", response_model=list[TripMessage], summary="Trip chat history")
async def chat_history(trip_id: str, user: CurrentUser, service: Service) -> list[TripMessage]:
    return await service.history(user, trip_id)


@router.post("/{trip_id}/share", response_model=ShareResponse, summary="Create a public read-only share link")
async def share_trip(trip_id: str, user: CurrentUser, service: Service) -> ShareResponse:
    return await service.share(user, trip_id)


@router.delete("/{trip_id}/share", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the share link")
async def unshare_trip(trip_id: str, user: CurrentUser, service: Service) -> None:
    await service.unshare(user, trip_id)


@shared_router.get("/trips/{token}", response_model=TripOut, summary="View a shared trip (no auth)")
async def get_shared_trip(token: str, service: Service) -> TripOut:
    return await service.get_shared(token)
