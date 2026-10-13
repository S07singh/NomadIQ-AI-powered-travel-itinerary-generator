from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status

from app.common.schemas import Page
from app.core.deps import DB, CurrentUser, PageParams, ProvidersDep, SettingsDep
from app.modules.bookings.schemas import BookingConfirm, BookingCreate, BookingOut, BookingStatus, BookingSummary
from app.modules.bookings.service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_service(db: DB, providers: ProvidersDep, settings: SettingsDep) -> BookingService:
    return BookingService(db, providers, settings)


Service = Annotated[BookingService, Depends(get_service)]


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED, summary="Quote an offer and create a booking awaiting confirmation")
async def create_booking(
    data: BookingCreate,
    user: CurrentUser,
    service: Service,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)] = None,
) -> BookingOut:
    return await service.create(user, data, idempotency_key)


@router.get("", response_model=Page[BookingSummary], summary="List my bookings")
async def list_bookings(
    user: CurrentUser,
    service: Service,
    paging: PageParams,
    status_filter: Annotated[BookingStatus | None, Query(alias="status")] = None,
    trip_id: str | None = None,
) -> Page[BookingSummary]:
    return await service.list_bookings(user, status_filter, trip_id, paging.page, paging.limit)


@router.get("/{booking_id}", response_model=BookingOut, summary="Get a booking")
async def get_booking(booking_id: str, user: CurrentUser, service: Service) -> BookingOut:
    return await service.get(user, booking_id)


@router.post("/{booking_id}/confirm", response_model=BookingOut, summary="Pay and book (requires the exact accepted price)")
async def confirm_booking(booking_id: str, data: BookingConfirm, user: CurrentUser, service: Service) -> BookingOut:
    return await service.confirm(user, booking_id, data)


@router.post("/{booking_id}/cancel", response_model=BookingOut, summary="Cancel a booking (refunds when supported)")
async def cancel_booking(booking_id: str, user: CurrentUser, service: Service) -> BookingOut:
    return await service.cancel(user, booking_id)
