from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.common.schemas import Page
from app.core.deps import DB, CurrentUser, JobsDep, PageParams, ProvidersDep, SettingsDep
from app.core.exceptions import AppError
from app.core.ratelimit import rate_limit
from app.modules.assistant.schemas import AssistantMessage, AssistantMessageRequest, AssistantReply, ConversationSummary
from app.modules.assistant.service import AssistantService
from app.providers.speech import Transcript

router = APIRouter(prefix="/assistant", tags=["Assistant (chatbot)"], dependencies=[Depends(rate_limit("assistant", per_minute=30))])
voice_router = APIRouter(prefix="/voice", tags=["Voice"], dependencies=[Depends(rate_limit("voice", per_minute=20))])


def get_service(db: DB, providers: ProvidersDep, settings: SettingsDep, jobs: JobsDep) -> AssistantService:
    return AssistantService(db, providers, settings, jobs)


Service = Annotated[AssistantService, Depends(get_service)]


@router.post("/messages", response_model=AssistantReply, summary="Send a message to the travel assistant")
async def send_message(req: AssistantMessageRequest, user: CurrentUser, service: Service) -> AssistantReply:
    return await service.handle(user, req)


@router.get("/conversations", response_model=Page[ConversationSummary], summary="List assistant conversations")
async def list_conversations(user: CurrentUser, service: Service, paging: PageParams) -> Page[ConversationSummary]:
    return await service.list_conversations(user, paging.page, paging.limit)


@router.get("/conversations/{conversation_id}/messages", response_model=list[AssistantMessage], summary="Conversation messages")
async def conversation_messages(conversation_id: str, user: CurrentUser, service: Service) -> list[AssistantMessage]:
    return await service.get_messages(user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a conversation")
async def delete_conversation(conversation_id: str, user: CurrentUser, service: Service) -> None:
    await service.delete_conversation(user, conversation_id)


# ─── Voice ────────────────────────────────────────────────────────

async def _read_audio(audio: UploadFile, max_bytes: int) -> bytes:
    content_type = (audio.content_type or "").lower()
    if not (content_type.startswith("audio/") or content_type in ("video/webm", "application/octet-stream")):
        raise AppError("Upload an audio file (m4a, mp3, wav, webm, ogg)", code="unsupported_media", status_code=415)
    data = await audio.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AppError(f"Audio must be under {max_bytes // (1024 * 1024)} MB", code="audio_too_large", status_code=413)
    if not data:
        raise AppError("Audio file is empty", code="audio_empty", status_code=422)
    return data


@voice_router.post("/transcribe", response_model=Transcript, summary="Speech → text")
async def transcribe(
    user: CurrentUser,
    providers: ProvidersDep,
    settings: SettingsDep,
    audio: Annotated[UploadFile, File(description="Recorded audio")],
    language: Annotated[str | None, Form(max_length=10)] = None,
) -> Transcript:
    data = await _read_audio(audio, settings.max_audio_bytes)
    return await providers.speech.transcribe(data, audio.content_type or "", language)


@voice_router.post("/assistant", response_model=AssistantReply, summary="Voice command → assistant (transcribe + act)")
async def voice_assistant(
    user: CurrentUser,
    providers: ProvidersDep,
    settings: SettingsDep,
    service: Service,
    audio: Annotated[UploadFile, File(description="Recorded audio")],
    conversation_id: Annotated[str | None, Form()] = None,
    trip_id: Annotated[str | None, Form()] = None,
    selected_offer_id: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form(max_length=10)] = None,
) -> AssistantReply:
    data = await _read_audio(audio, settings.max_audio_bytes)
    transcript = await providers.speech.transcribe(data, audio.content_type or "", language)
    if not transcript.text.strip():
        raise AppError("Sorry, I couldn't hear anything. Please try again.", code="no_speech", status_code=422)
    req = AssistantMessageRequest(message=transcript.text[:2000], conversation_id=conversation_id or None, trip_id=trip_id or None, selected_offer_id=selected_offer_id or None)
    return await service.handle(user, req, transcript=transcript.text)
