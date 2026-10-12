"""
Duffel flights provider (https://duffel.com/docs/api). Replaces Amadeus
Self-Service, which shut down in July 2026.

Flow: offer_requests (search) -> offers/{id} (re-price) -> orders (book)
      -> order_cancellations (+ confirm) (cancel).
Offers expire ~30 min after search, so the booking flow always re-quotes.
"""

import re
from datetime import datetime

import httpx

from app.common.schemas import Money
from app.common.travel import (
    BaseOffer,
    ContactInfo,
    FlightOffer,
    FlightSearchRequest,
    FlightSegment,
    FlightSlice,
    PassengerType,
    ProviderBookingResult,
    TravelerInfo,
)
from app.core.exceptions import ProviderError
from app.providers.base import Airport, FlightProvider

BASE_URL = "https://api.duffel.com"
_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?")


def parse_iso_duration(value: str | None) -> int:
    if not value:
        return 0
    m = _DURATION.fullmatch(value)
    if not m:
        return 0
    days, hours, minutes = (int(x or 0) for x in m.groups())
    return days * 1440 + hours * 60 + minutes


def parse_offer(data: dict, passengers: int) -> FlightOffer:
    slices = []
    for s in data.get("slices", []):
        segs = [
            FlightSegment(
                carrier=seg["marketing_carrier"]["name"],
                carrier_code=seg["marketing_carrier"]["iata_code"],
                flight_number=f"{seg['marketing_carrier']['iata_code']}{seg.get('marketing_carrier_flight_number', '')}",
                origin=seg["origin"]["iata_code"],
                destination=seg["destination"]["iata_code"],
                departure_at=datetime.fromisoformat(seg["departing_at"]),
                arrival_at=datetime.fromisoformat(seg["arriving_at"]),
                aircraft=(seg.get("aircraft") or {}).get("name"),
            )
            for seg in s.get("segments", [])
        ]
        slices.append(
            FlightSlice(
                origin=s["origin"]["iata_code"],
                destination=s["destination"]["iata_code"],
                departure_at=segs[0].departure_at,
                arrival_at=segs[-1].arrival_at,
                duration_minutes=parse_iso_duration(s.get("duration")),
                stops=max(len(segs) - 1, 0),
                segments=segs,
            )
        )
    owner = data.get("owner") or {}
    refund = ((data.get("conditions") or {}).get("refund_before_departure") or {}).get("allowed", False)
    return FlightOffer(
        offer_id=f"duffel:{data['id']}",
        provider="duffel",
        title=f"{owner.get('name', 'Flight')} {slices[0].origin}→{slices[0].destination}" if slices else owner.get("name", "Flight"),
        price=Money(amount=float(data["total_amount"]), currency=data["total_currency"]),
        refundable=bool(refund),
        expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        slices=slices,
        passengers=passengers,
        airline_logo_url=owner.get("logo_symbol_url"),
    )


class DuffelFlightProvider(FlightProvider):
    name = "duffel"

    def __init__(self, http: httpx.AsyncClient, token: str):
        if not token:
            raise RuntimeError("DUFFEL_API_TOKEN is required for FLIGHT_PROVIDER=duffel")
        self.http = http
        self.headers = {"Authorization": f"Bearer {token}", "Duffel-Version": "v2", "Accept": "application/json", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = await self.http.request(method, f"{BASE_URL}{path}", headers=self.headers, **kwargs)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Duffel unreachable: {exc}")
        if resp.status_code >= 400:
            errors = resp.json().get("errors", []) if resp.headers.get("content-type", "").startswith("application/json") else []
            msg = errors[0].get("message") if errors else resp.text[:200]
            raise ProviderError(f"Duffel error: {msg}", details=errors or None)
        return resp.json()

    async def search(self, req: FlightSearchRequest) -> list[FlightOffer]:
        slices = [{"origin": req.origin, "destination": req.destination, "departure_date": req.departure_date.isoformat()}]
        if req.return_date:
            slices.append({"origin": req.destination, "destination": req.origin, "departure_date": req.return_date.isoformat()})
        passengers = [{"type": "adult"}] * req.adults + [{"age": 10}] * req.children + [{"type": "infant_without_seat"}] * req.infants
        body: dict = {"data": {"slices": slices, "passengers": passengers, "cabin_class": req.cabin_class.value}}
        if req.non_stop_only:
            body["data"]["max_connections"] = 0
        data = await self._request("POST", "/air/offer_requests", params={"return_offers": "true", "supplier_timeout": 10000}, json=body)
        offers = data["data"].get("offers", [])
        offers.sort(key=lambda o: float(o["total_amount"]))
        pax = len(passengers)
        return [parse_offer(o, pax) for o in offers[: req.max_results]]

    async def suggest_airports(self, query: str, limit: int = 8) -> list[Airport]:
        data = await self._request("GET", "/places/suggestions", params={"query": query})
        out = []
        for p in data.get("data", []):
            if p.get("type") == "airport":
                out.append(Airport(iata_code=p["iata_code"], name=p["name"], city=p.get("city_name") or "", country_code=p.get("iata_country_code") or ""))
        return out[:limit]

    async def quote(self, offer: BaseOffer) -> BaseOffer:
        raw_id = offer.offer_id.split(":", 1)[1]
        data = await self._request("GET", f"/air/offers/{raw_id}", params={"return_available_services": "false"})
        return parse_offer(data["data"], getattr(offer, "passengers", 1))

    async def book(self, offer: BaseOffer, travelers: list[TravelerInfo], contact: ContactInfo) -> ProviderBookingResult:
        raw_id = offer.offer_id.split(":", 1)[1]
        live = (await self._request("GET", f"/air/offers/{raw_id}"))["data"]
        pax_ids = [p["id"] for p in live.get("passengers", [])]
        if len(pax_ids) != len(travelers):
            raise ProviderError("Traveler count does not match the offer", code="traveler_mismatch", status_code=422)
        passengers = []
        for pid, t in zip(pax_ids, travelers):
            if not (t.born_on and t.gender and t.title):
                raise ProviderError("Flights require title, gender and date of birth for every traveler", code="traveler_incomplete", status_code=422)
            passengers.append({
                "id": pid,
                "given_name": t.given_name,
                "family_name": t.family_name,
                "born_on": t.born_on.isoformat(),
                "gender": "m" if t.gender == "m" else "f",
                "title": t.title,
                "email": str(t.email or contact.email),
                "phone_number": t.phone or contact.phone,
            })
        body = {"data": {"type": "instant", "selected_offers": [raw_id], "passengers": passengers,
                         "payments": [{"type": "balance", "currency": live["total_currency"], "amount": live["total_amount"]}]}}
        order = (await self._request("POST", "/air/orders", json=body))["data"]
        return ProviderBookingResult(
            provider_reference=order["booking_reference"],
            status="confirmed",
            tickets=[d.get("unique_identifier", "") for d in order.get("documents", [])],
            raw={"order_id": order["id"]},
        )

    async def cancel(self, provider_reference: str, provider_data: dict) -> bool:
        order_id = provider_data.get("order_id")
        if not order_id:
            raise ProviderError("Missing Duffel order id", code="cancel_failed")
        pending = (await self._request("POST", "/air/order_cancellations", json={"data": {"order_id": order_id}}))["data"]
        await self._request("POST", f"/air/order_cancellations/{pending['id']}/actions/confirm")
        return True
