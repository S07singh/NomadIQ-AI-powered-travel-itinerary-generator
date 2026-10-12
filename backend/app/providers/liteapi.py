"""
LiteAPI hotels provider (https://docs.liteapi.travel).

Flow: POST /hotels/rates (search) -> POST /rates/prebook -> POST /rates/book
      -> PUT /bookings/{id} (cancel).
Response parsing is defensive; verify field names against the sandbox before go-live.
"""

import httpx

from app.common.schemas import MediaImage, Money
from app.common.travel import BaseOffer, ContactInfo, HotelOffer, HotelSearchRequest, ProviderBookingResult, TravelerInfo
from app.core.exceptions import AppError, ProviderError
from app.providers.base import HotelProvider

API_URL = "https://api.liteapi.travel/v3.0"
BOOK_URL = "https://book.liteapi.travel/v3.0"


def parse_rates(payload: dict, req: HotelSearchRequest) -> list[HotelOffer]:
    hotels_meta = {h.get("id"): h for h in payload.get("hotels", []) or []}
    offers = []
    for item in payload.get("data", []) or []:
        hotel_id = item.get("hotelId")
        meta = hotels_meta.get(hotel_id, {})
        room_types = item.get("roomTypes") or []
        if not room_types:
            continue
        room = min(room_types, key=lambda r: float((r.get("offerRetailRate") or {}).get("amount", 1e12)))
        total = room.get("offerRetailRate") or {}
        rate = (room.get("rates") or [{}])[0]
        if "amount" not in total:
            continue
        amount, currency = float(total["amount"]), total.get("currency", req.currency)
        refundable = (rate.get("cancellationPolicies") or {}).get("refundableTag") == "RFN"
        name = meta.get("name") or f"Hotel {hotel_id}"
        photo = meta.get("main_photo")
        offers.append(
            HotelOffer(
                offer_id=f"liteapi:{room['offerId']}",
                provider="liteapi",
                title=name,
                hotel_id=str(hotel_id),
                name=name,
                address=meta.get("address", ""),
                city=req.city,
                star_rating=meta.get("stars"),
                review_score=meta.get("rating"),
                lat=meta.get("latitude"),
                lng=meta.get("longitude"),
                images=[MediaImage(url=photo, alt=name, source="liteapi")] if photo else [],
                room_name=rate.get("name", ""),
                board_type=(rate.get("boardName") or "room_only").lower().replace(" ", "_"),
                check_in=req.check_in,
                check_out=req.check_out,
                nights=req.nights,
                price=Money(amount=amount, currency=currency),
                price_per_night=Money(amount=round(amount / req.nights, 2), currency=currency),
                refundable=refundable,
                cancellation_policy="Refundable" if refundable else "Non-refundable",
            )
        )
    offers.sort(key=lambda o: o.price.amount)
    return offers[: req.max_results]


class LiteApiHotelProvider(HotelProvider):
    name = "liteapi"

    def __init__(self, http: httpx.AsyncClient, api_key: str):
        if not api_key:
            raise RuntimeError("LITEAPI_API_KEY is required for HOTEL_PROVIDER=liteapi")
        self.http = http
        self.headers = {"X-API-Key": api_key, "Accept": "application/json"}

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            resp = await self.http.request(method, url, headers=self.headers, **kwargs)
        except httpx.HTTPError as exc:
            raise ProviderError(f"LiteAPI unreachable: {exc}")
        if resp.status_code >= 400:
            raise ProviderError(f"LiteAPI error {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    async def search(self, req: HotelSearchRequest) -> list[HotelOffer]:
        if not req.country_code:
            raise AppError("country_code is required for hotel search", code="country_code_required", status_code=422)
        body = {
            "cityName": req.city,
            "countryCode": req.country_code.upper(),
            "checkin": req.check_in.isoformat(),
            "checkout": req.check_out.isoformat(),
            "currency": req.currency,
            "guestNationality": req.country_code.upper(),
            "occupancies": [{"adults": max(1, req.adults // req.rooms), "children": [8] * (req.children // req.rooms)}] * req.rooms,
            "limit": req.max_results,
            "includeHotelData": True,
        }
        return parse_rates(await self._request("POST", f"{API_URL}/hotels/rates", json=body), req)

    async def book(self, offer: BaseOffer, travelers: list[TravelerInfo], contact: ContactInfo) -> ProviderBookingResult:
        raw_id = offer.offer_id.split(":", 1)[1]
        prebook = (await self._request("POST", f"{BOOK_URL}/rates/prebook", json={"offerId": raw_id, "usePaymentSdk": False}))["data"]
        lead = travelers[0]
        body = {
            "prebookId": prebook["prebookId"],
            "holder": {"firstName": lead.given_name, "lastName": lead.family_name, "email": str(contact.email), "phone": contact.phone},
            "payment": {"method": "ACC_CREDIT_CARD"},
            "guests": [{"occupancyNumber": 1, "firstName": lead.given_name, "lastName": lead.family_name, "email": str(contact.email)}],
        }
        booking = (await self._request("POST", f"{BOOK_URL}/rates/book", json=body))["data"]
        status = "confirmed" if str(booking.get("status", "")).upper() == "CONFIRMED" else "pending"
        return ProviderBookingResult(
            provider_reference=booking.get("hotelConfirmationCode") or booking["bookingId"],
            status=status,
            raw={"booking_id": booking["bookingId"]},
        )

    async def cancel(self, provider_reference: str, provider_data: dict) -> bool:
        booking_id = provider_data.get("booking_id", provider_reference)
        await self._request("PUT", f"{BOOK_URL}/bookings/{booking_id}")
        return True

