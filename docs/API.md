# NomadIQ API v1 — Reference

Base URL: `http://localhost:8000/api/v1` · Interactive docs: `/api/v1/docs` · OpenAPI: `/api/v1/openapi.json`

One API for the **website (Next.js)** and the **mobile app (React Native/Expo)**:

- Auth: `Authorization: Bearer <access_token>` (30 min). Rotate with `/auth/refresh` (refresh token, 30 days, single-use).
- Errors: always `{"error": {"code": "...", "message": "...", "details": ...}}`.
- Pagination: `?page=1&limit=20` → `{items, total, page, limit, has_more}`.
- Dates `YYYY-MM-DD`, timestamps ISO-8601 UTC, money `{"amount": 123.45, "currency": "INR"}`.
- 🔒 = requires auth.

## Meta
| Method | Path | Response | Notes |
|---|---|---|---|
| GET | `/health` | `{status, time}` | liveness |
| GET | `/health/ready` | `{status, mongo, active_jobs}` | readiness (503 if Mongo down) |
| GET | `/meta/config` | `ClientConfig` | enums, feature flags, `min_mobile_app_version` for force-update |

## Auth
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `RegisterRequest {email, password(8-72, letters+digits), name}` | 201 `AuthResponse {user, tokens}` |
| POST | `/auth/login` | `LoginRequest {email, password}` | `AuthResponse` |
| POST | `/auth/refresh` | `RefreshRequest {refresh_token}` | `TokenPair` (old token revoked; reuse revokes all sessions) |
| POST | `/auth/logout` | `RefreshRequest` | 204 |
| POST | `/auth/password/change` 🔒 | `ChangePasswordRequest {current_password, new_password}` | 204 (signs out other sessions) |

`TokenPair {access_token, refresh_token, token_type, expires_in}` · rate-limited per IP.

## Users 🔒
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/users/me` | — | `UserOut {id, email, name, avatar_url, preferences, created_at}` |
| PATCH | `/users/me` | `UserUpdate {name?, avatar_url?, preferences?: UserPreferencesUpdate}` | `UserOut` (preferences merged) |
| DELETE | `/users/me` | — | 204 — deletes personal data, anonymises bookings |
| GET | `/users/me/travelers` | — | `TravelerOut[]` |
| POST | `/users/me/travelers` | `TravelerCreate {label, title, given_name, family_name, born_on, gender, email, phone, nationality, passport_number, passport_expiry}` | 201 `TravelerOut` (max 20) |
| PATCH | `/users/me/travelers/{id}` | `TravelerUpdate` (partial) | `TravelerOut` |
| DELETE | `/users/me/travelers/{id}` | — | 204 |
| POST | `/users/me/devices` | `DeviceRegister {token, platform: ios/android/web, app_version}` | `DeviceOut` (upsert by token) |
| DELETE | `/users/me/devices/{token}` | — | 204 |

`UserPreferences {home_city, home_airport, currency, language, travel_style, dietary[], interests[], notifications_enabled}`

## Trips 🔒
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/trips` | `TripCreate` | 201 `TripOut` (`status=queued` when `generate=true`) |
| GET | `/trips?status=&page=&limit=` | — | `Page[TripSummary]` |
| GET | `/trips/{id}` | — | `TripOut` (with `plan`) |
| PATCH | `/trips/{id}` | `TripUpdate` (partial inputs) | `TripOut` (409 while generating) |
| DELETE | `/trips/{id}` | — | 204 |
| POST | `/trips/{id}/generate` | — | 202 `TripOut` (409 if already running) |
| GET | `/trips/{id}/status` | — | `TripProgress {status, step, percent, message, updated_at}` |
| GET | `/trips/{id}/events` | — | `text/event-stream`: `progress` events → `done` |
| POST | `/trips/{id}/chat` | `TripChatRequest {message}` | `TripChatResponse {reply, plan_updated, trip}` (409 if not ready) |
| GET | `/trips/{id}/chat` | — | `TripMessage[]` |
| POST | `/trips/{id}/share` | — | `ShareResponse {share_token, share_url}` |
| DELETE | `/trips/{id}/share` | — | 204 |
| GET | `/shared/trips/{token}` (public) | — | `TripOut` (private notes removed) |

`TripCreate {title?, destination, origin?, start_date?, end_date?, duration_days?(1-30), travelers{adults,children,infants}, budget?{amount,currency,flexible}, travel_style: backpacker|budget|comfort|luxury, pace: relaxed|moderate|packed, vibes[], interests[], dietary[], additional_info, generate=true}`
— dates are normalised: start+end → duration; start+duration → end; neither → 3 days.

`TripStatus`: `draft → queued → generating → ready | failed`

`TripPlan {summary, highlights[], location: Place, cover_image, gallery[MediaImage], videos[VideoLink], days[DayPlan], attractions[Attraction], hotels[HotelSuggestion], restaurants[RestaurantSuggestion], local_dishes[], budget: BudgetBreakdown, local_info, packing_list[], travel_tips[], weather[WeatherDay], generated_at, generation_ms, ai_model}`
- `DayPlan {day, date, title, items[ItineraryItem], notes, weather}`
- `ItineraryItem {time_of_day, start_time, title, description, place_name, kind: activity|meal|transport|rest|hotel, estimated_cost, duration_hours, maps_url, image}`
- `Attraction {name, description, area, category, estimated_cost, visit_duration_hours, best_time, booking_required, maps_url, images[], videos[]}`
- `HotelSuggestion {name, area, price_per_night, rating, amenities[], why, maps_url, images[], search_hint}` — `search_hint` is a ready body for `POST /search/hotels`
- `BudgetBreakdown {currency, total, per_person, per_day, lines[{category, amount, note}], budget_limit, within_budget, tips[]}`

## Search 🔒 (live inventory)
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/search/flights` | `FlightSearchRequest {origin, destination (IATA), departure_date, return_date?, adults, children, infants, cabin_class, currency, non_stop_only, max_results}` | `SearchResponse[FlightOffer]` |
| POST | `/search/hotels` | `HotelSearchRequest {city, country_code?, check_in, check_out, adults, children, rooms, currency, min_rating?, max_price_per_night?}` | `SearchResponse[HotelOffer]` |
| POST | `/search/trains` | `GroundSearchRequest {origin, destination, date, passengers, travel_class?, currency}` | `SearchResponse[TransportOffer]` |
| POST | `/search/buses` | `GroundSearchRequest` | `SearchResponse[TransportOffer]` |
| POST | `/search/activities` | `ActivitySearchRequest {destination, date?, query?, currency}` | `SearchResponse[ActivityOffer]` |
| GET | `/search/airports?q=` | — | `Airport[] {iata_code, name, city, country_code}` |
| GET | `/search/offers/{offer_id}` | — | offer (410 `offer_expired` after TTL) |

`SearchResponse {kind, provider, count, results[], cached, searched_at}` · every offer has `offer_id = "<provider>:<id>"`, `price`, `expires_at`, `refundable`.

## Bookings 🔒
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/bookings` (+ `Idempotency-Key` header) | `BookingCreate {offer_id, traveler_ids[] \| travelers[], contact{email, phone}, trip_id?, notes}` | 201 `BookingOut` `status=awaiting_confirmation` (re-quoted price, payment intent) |
| POST | `/bookings/{id}/confirm` | `BookingConfirm {expected_total: Money, payment_token?}` | `BookingOut` `confirmed` / `failed`(refunded) · 409 `price_mismatch` · 402 `payment_failed` · 410 `offer_expired` |
| POST | `/bookings/{id}/cancel` | — | `BookingOut` `cancelled` (refund) |
| GET | `/bookings?status=&trip_id=` | — | `Page[BookingSummary]` |
| GET | `/bookings/{id}` | — | `BookingOut` |

`BookingOut {id, status, kind, provider, offer, price, original_price, price_changed, travelers[], contact, trip_id, provider_reference (PNR), tickets[], payment{intent_id, provider, status, amount, client_secret}, confirm_before, failure_reason, timestamps}`

## Explore (public, rate-limited)
| Method | Path | Response |
|---|---|---|
| GET | `/explore/places?q=&limit=` | `Place[] {name, country, country_code, region, lat, lng, timezone}` |
| GET | `/explore/destination?q=` | `DestinationOverview {place, summary, images[], videos[], weather[7], maps_url}` |
| GET | `/explore/images?q=&limit=` | `MediaImage[] {url, thumbnail_url, width, height, alt, attribution, source, source_url}` |
| GET | `/explore/videos?q=&limit=` | `VideoLink[] {title, url, thumbnail_url, channel, source}` |
| GET | `/explore/weather?lat=&lng=&start=&end=` | `WeatherDay[] {date, temp_min_c, temp_max_c, precipitation_mm, precipitation_probability, condition, sunrise, sunset}` |

## Assistant 🔒 (chatbot)
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/assistant/messages` | `AssistantMessageRequest {message, conversation_id?, trip_id?, selected_offer_id?}` | `AssistantReply {conversation_id, message, transcript}` |
| GET | `/assistant/conversations` | — | `Page[ConversationSummary]` |
| GET | `/assistant/conversations/{id}/messages` | — | `AssistantMessage[]` |
| DELETE | `/assistant/conversations/{id}` | — | 204 |

`AssistantMessage {id, role, content, intent, actions[], created_at}` — intents: `chat, plan_trip, search_flights, search_hotels, search_trains, search_buses, search_activities, book_offer, modify_trip`.
Action types the UI renders: `show_offers {kind, total, results[]}`, `trip_created {trip_id}`, `trip_updated {trip_id, plan_version}`, `booking_quote {booking_id, requires_confirmation: true, price, confirm_before}`, `needs_info {missing[]}`.

## Voice 🔒 (multipart/form-data)
| Method | Path | Form fields | Response |
|---|---|---|---|
| POST | `/voice/transcribe` | `audio` (file ≤10 MB), `language?` | `Transcript {text, language, confidence, duration_seconds}` |
| POST | `/voice/assistant` | `audio`, `conversation_id?`, `trip_id?`, `selected_offer_id?`, `language?` | `AssistantReply` (+ `transcript`) |

Speak the reply on-device (expo-speech / Web Speech API).

## Client flows

**Plan a trip** → `POST /trips` → open `GET /trips/{id}/events` (SSE; mobile can poll `/status`) → on `done` fetch `GET /trips/{id}`.

**Book from a plan** → `hotel.search_hint` → `POST /search/hotels` → `POST /bookings` (Idempotency-Key) → show price + `confirm_before` → payment SDK → `POST /bookings/{id}/confirm {expected_total, payment_token}`.

**Voice booking** → `POST /voice/assistant` ("flights to Goa Friday") → `show_offers` → user taps one → `POST /voice/assistant` ("book this", `selected_offer_id`) → `booking_quote` → user taps **Confirm** → `/bookings/{id}/confirm`.
