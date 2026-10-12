"""Abstract interfaces for bookable inventory providers."""

from abc import ABC, abstractmethod

from app.common.travel import (
    ActivityOffer,
    ActivitySearchRequest,
    BaseOffer,
    ContactInfo,
    FlightOffer,
    FlightSearchRequest,
    GroundSearchRequest,
    HotelOffer,
    HotelSearchRequest,
    OfferKind,
    ProviderBookingResult,
    TransportOffer,
    TravelerInfo,
)
from app.common.schemas import APIModel
from app.core.exceptions import ProviderError


class Airport(APIModel):
    iata_code: str
    name: str
    city: str
    country_code: str


class InventoryProvider(ABC):
    name: str = "base"

    async def quote(self, offer: BaseOffer) -> BaseOffer:
        """Re-confirm price/availability right before booking. Default: unchanged."""
        return offer

    @abstractmethod
    async def book(self, offer: BaseOffer, travelers: list[TravelerInfo], contact: ContactInfo) -> ProviderBookingResult: ...

    async def cancel(self, provider_reference: str, provider_data: dict) -> bool:
        raise ProviderError("This provider does not support cancellation", code="cancel_unsupported", status_code=409)


class FlightProvider(InventoryProvider):
    @abstractmethod
    async def search(self, req: FlightSearchRequest) -> list[FlightOffer]: ...

    @abstractmethod
    async def suggest_airports(self, query: str, limit: int = 8) -> list[Airport]: ...


class HotelProvider(InventoryProvider):
    @abstractmethod
    async def search(self, req: HotelSearchRequest) -> list[HotelOffer]: ...


class GroundProvider(InventoryProvider):
    @abstractmethod
    async def search(self, mode: OfferKind, req: GroundSearchRequest) -> list[TransportOffer]: ...


class ActivityProvider(InventoryProvider):
    @abstractmethod
    async def search(self, req: ActivitySearchRequest) -> list[ActivityOffer]: ...
