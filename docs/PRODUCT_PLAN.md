# NomadIQ — Product Plan

Goal: turn NomadIQ from an AI itinerary demo into a travel app people use end-to-end:
**discover → plan → see it (photos/videos/maps/weather) → book (flight/train/bus/hotel/activity) → travel**,
on the website and a React Native app, all served by one backend.

_Last updated: 2026-10-13_

---

## 1. Where we are vs. the market

| Capability | NomadIQ v1 | NomadIQ v2 backend (this release) | Market reference |
|---|---|---|---|
| AI itinerary | Sequential 5 agents + slow 2nd LLM pass to convert markdown→JSON | 4 agents, 3 run **in parallel**, LLM returns **typed JSON directly**; budget computed in code | Mindtrip, Layla, Wanderboat |
| Visuals | None | Photos (Wikipedia/Unsplash/Pexels), YouTube videos, Google-Maps deep links, cover + gallery | Mindtrip, Google Travel |
| Live data | None | Weather forecast + geocoding (Open-Meteo), destination summaries | — |
| Booking | None | Search + **quote → explicit confirm** booking state machine for flights, hotels, trains, buses, activities | Mindtrip Flights (Sabre + PayPal), Layla, MakeMyTrip |
| Chat | Edits plan JSON only | Trip editor chat **plus** a global assistant that searches, plans and prepares bookings | Layla, Mindtrip |
| Voice | None | Speech-to-text → assistant → action (booking still needs a tap to confirm) | — |
| Clients | Next.js only, SQLite + separate Prisma DB | One `/api/v1` for web + mobile, MongoDB (local → Atlas), JWT | — |

Our differentiators: **India-first ground transport (trains/buses)** plus global flights/hotels, **voice in Hindi/English**, budget accuracy (computed, not hallucinated), and a single assistant that goes from idea to booking.

---

## 2. Research findings that shaped the design

- **Flights** — Amadeus Self-Service APIs were decommissioned in July 2026; **Duffel** is the practical self-serve option (REST, sandbox, pay-per-order, 300+ airlines). Offers expire ~30 min → we always re-quote before booking. Implemented: `providers/duffel.py`.
- **Hotels** — **LiteAPI** (self-serve search/prebook/book/cancel) for launch; add Booking.com affiliate or Hotelbeds (wholesale, contract) later for margin. Implemented: `providers/liteapi.py`.
- **Trains & buses (India)** — no public IRCTC API; access is via authorised partners (redBus/redRail SeatSeller, RailYatri, ConfirmTkt, Travelport-type aggregators) under a commercial agreement. International rail/bus: Trainline Partner Solutions, 12Go, Omio. Backend has the `GroundProvider` interface + mock; plug the partner in when signed.
- **Activities** — Viator Partner API (affiliate → full + booking access, certification required) and GetYourGuide Partner API.
- **Images** — Wikipedia/Wikimedia (free, no key, best for landmarks) by default; Unsplash (50 req/h demo, attribution required) and Pexels (200 req/h) as alternatives; Google Places Photos when we need exact restaurant/hotel photos (paid).
- **Videos** — YouTube Data API `search.list` costs 100 of 10,000 daily quota units → default to **zero-cost YouTube search links**; switch on the API with aggressive caching.
- **Weather/geocoding** — Open-Meteo: free, key-less, very fast, 16-day forecast (commercial plan above 10k req/day).
- **Voice** — Deepgram Nova-3 (streaming, ~sub-300 ms, ~$0.0077/min, Hindi/English) for real-time; OpenAI transcription as fallback. Text-to-speech on device (expo-speech / Web Speech API) = zero added latency.
- **Database** — Motor is deprecated (EOL 2026); use **PyMongo Async API** (done).
- **Web scraping** — use official/partner APIs first. Scraping OTA or Google pages breaks ToS and is brittle; only consider it for public, permitted sources (e.g. official tourism sites, event calendars), behind the same provider interface, with caching and robots.txt compliance.

---

## 3. Feature roadmap

### Phase 1 — Backend foundation ✅ (this release)
- Modular FastAPI backend, `/api/v1`, OpenAPI docs, single error envelope.
- Auth: register/login, rotating refresh tokens with reuse detection, change password, account deletion (store requirement).
- Users: preferences, **saved travelers** (one-tap/voice booking), push device registry.
- Trips: create → background AI planning → progress (polling + **SSE**), regenerate, edit inputs, chat edits with versioning, public share links.
- Plan enrichment: photos, videos, maps links, weather per day, computed budget vs. limit.
- Search: flights, hotels, trains, buses, activities, airport autocomplete; result caching + offer store.
- Bookings: quote → confirm (price guard, idempotency key, payment capture) → confirmed / failed+refund / cancel.
- Assistant chatbot + voice endpoints with safe action execution.
- Explore: destination overview (photos, summary, videos, 7-day weather, map), image/video/weather search, place autocomplete.
- 76 automated tests against real MongoDB.

### Phase 2 — Real inventory & payments (needs business accounts)
- Duffel live token, LiteAPI live key, Viator affiliate → full-booking access.
- Indian rail/bus partner integration (redBus SeatSeller / RailYatri / ConfirmTkt) → implement `GroundProvider`.
- Payments: **Razorpay** (UPI, cards, wallets — India) and **Stripe** (global) behind `PaymentProvider`; payment webhooks endpoint; receipts/invoices (GST).
- Booking webhooks from suppliers (schedule changes, cancellations) → push notifications.
- E-ticket / voucher PDFs in-app, add-to-calendar (.ics).

### Phase 3 — Mobile app (React Native / Expo)
- Screens: onboarding/preferences, explore feed, trip builder, live generation (SSE), itinerary with photo cards + map view, search & compare, checkout, bookings wallet, assistant with push-to-talk, offline trip cache.
- Push notifications (Expo push → FCM/APNs): plan ready, price drops, check-in reminders, gate/schedule changes.
- Deep links / universal links for shared trips.

### Phase 4 — Delight & retention
- **Streaming chat** (token streaming over SSE) and **streaming voice** (WebSocket → Deepgram live) for sub-second responses.
- Price alerts & fare tracking (scheduled jobs).
- Collaborative trips (invite friends, vote on activities, split costs).
- Packing checklist, document vault (passport/visa reminders), visa requirement lookup.
- Local transport routing (Google Directions / OSRM), offline maps.
- Reviews & UGC photos; creator itineraries ("copy this trip").
- Multi-language UI and Hindi/regional voice.

### Phase 5 — Scale & business
- Redis (cache, rate limits, pub/sub for SSE), ARQ/Celery workers for generation, horizontal API replicas.
- Observability: OpenTelemetry traces, Sentry, LLM cost/latency dashboards.
- Revenue: booking commissions/markups, affiliate links, premium plan (unlimited AI, price alerts, concierge).
- Compliance: PCI via payment SDKs (never store cards), DPDP Act (India)/GDPR data export & delete, passport data encryption at rest (field-level).

---

## 4. Latency strategy

| Technique | Where |
|---|---|
| Parallel agents (`asyncio.gather`) — cuts generation by ~40-60% | `planner/orchestrator.py` |
| Direct structured JSON from the LLM (Ollama `format`, Gemini JSON mode) — no second conversion pass | `providers/llm.py` |
| Budget computed in code (no LLM call) | `planner/budget.py` |
| L1 in-process + L2 Mongo TTL cache for media, geocoding, weather, search results | `core/cache.py` |
| Concurrency-limited, time-boxed, best-effort enrichment (never blocks the plan) | `planner/enrichment.py` |
| Shared pooled `httpx.AsyncClient` (keep-alive) | `main.py` |
| SSE progress instead of client polling storms | `trips/router.py` |
| GZip responses; list endpoints exclude heavy `plan` field | `main.py`, `trips/service.py` |
| Zero-quota video links, on-device TTS | `providers/media.py`, clients |

Measured locally (mock LLM, live Wikipedia + Open-Meteo): full 3-day plan with enrichment **~1.2 s**; destination overview **2.2 s cold → 4 ms cached**.
With a real LLM, generation time ≈ max(destination, hotel, dining) + itinerary ≈ 2 LLM round-trips.

---

## 5. Safety rules for auto-booking (voice/chat)

1. Assistant/voice can **search** and **quote**, never **confirm**.
2. `/bookings/{id}/confirm` requires `expected_total` equal to the quoted price (price guard) and a payment token from the user's device.
3. `Idempotency-Key` on create; confirm is idempotent and race-safe (atomic state transition).
4. Supplier failure after payment → automatic refund + `failed` status with reason.
5. Quotes expire with the supplier offer (`confirm_before`) → `410 offer_expired`.
