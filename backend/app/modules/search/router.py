from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.common.travel import (
    ActivityOffer,
    ActivitySearchRequest,
    AnyOffer,
    FlightOffer,
    FlightSearchRequest,
    GroundSearchRequest,
    HotelOffer,
    HotelSearchRequest,
    OfferKind,
    TransportOffer,
)
from app.core.deps import DB, CurrentUser, ProvidersDep, SettingsDep
from app.core.ratelimit import rate_limit
from app.modules.search.schemas import SearchResponse
from app.modules.search.service import SearchService
from app.providers.base import Airport

router = APIRouter(prefix="/search", tags=["Search & live inventory"], dependencies=[Depends(rate_limit("search", per_minute=60))])


def get_service(db: DB, providers: ProvidersDep, settings: SettingsDep) -> SearchService:
    return SearchService(db, providers, settings)


Service = Annotated[SearchService, Depends(get_service)]


@router.post("/flights", response_model=SearchResponse[FlightOffer], summary="Search live flight offers")
async def search_flights(req: FlightSearchRequest, _: CurrentUser, service: Service):
    return await service.flights(req)


@router.post("/hotels", response_model=SearchResponse[HotelOffer], summary="Search live hotel rates")
async def search_hotels(req: HotelSearchRequest, _: CurrentUser, service: Service):
    return await service.hotels(req)


@router.post("/trains", response_model=SearchResponse[TransportOffer], summary="Search trains")
async def search_trains(req: GroundSearchRequest, _: CurrentUser, service: Service):
    return await service.ground(OfferKind.train, req)


@router.post("/buses", response_model=SearchResponse[TransportOffer], summary="Search buses")
async def search_buses(req: GroundSearchRequest, _: CurrentUser, service: Service):
    return await service.ground(OfferKind.bus, req)


@router.post("/activities", response_model=SearchResponse[ActivityOffer], summary="Search tours & activities")
async def search_activities(req: ActivitySearchRequest, _: CurrentUser, service: Service):
    return await service.activities(req)


@router.get("/airports", response_model=list[Airport], summary="Airport autocomplete")
async def airports(q: Annotated[str, Query(min_length=2, max_length=50)], _: CurrentUser, service: Service):
    return await service.airports(q)


@router.get("/offers/{offer_id}", response_model=AnyOffer, summary="Get a previously returned offer (410 when expired)")
async def get_offer(offer_id: str, _: CurrentUser, service: Service):
    return await service.get_offer(offer_id)
