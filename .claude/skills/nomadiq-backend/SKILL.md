---
name: nomadiq-backend
description: Work on NomadIQ, the AI travel planner: FastAPI + MongoDB backend shared by the Next.js website (frontend/) and the Expo React Native app (mobile/). Use when adding or changing API routes, Pydantic schemas, feature modules, provider integrations (LLM, Duffel flights, LiteAPI hotels, trains/buses, images, videos, weather, speech, payments), trip planning agents, booking flow, assistant/voice, backend tests, or the website and mobile screens that use the API.
---

# NomadIQ backend

Product context and roadmap: `docs/PRODUCT_PLAN.md`. Every route + model: `docs/API.md`. Keep both in sync with code changes.

## Layout (`backend/app/`)

| Folder | Holds | Rule |
|---|---|---|
| `core/` | config (pydantic-settings), `database.py` (PyMongo **Async**, indexes), `security.py` (JWT/bcrypt), `deps.py`, `cache.py` (L1 dict + L2 Mongo TTL), `ratelimit.py`, `jobs.py`, `exceptions.py` | No feature logic |
| `common/` | `schemas.py` (APIModel, Page, Money, MediaImage, VideoLink, Place, WeatherDay, enums), `travel.py` (search requests, offers, TravelerInfo), `fx.py` | Shared by providers and modules |
| `providers/` | ABC per integration + `Mock*` + real impl; `registry.py` builds `Providers` from settings | Modules never call external HTTP directly |
| `modules/<feature>/` | `router.py` (thin) → `service.py` (logic, takes db/providers/settings) → `schemas.py` | One folder per feature |

Modules: `auth, users, trips, planner, search, bookings, explore, assistant (+voice), meta`. Routers are registered in `app/main.py:ROUTERS` under `settings.api_prefix` (`/api/v1`).

## Conventions

- **One API for web + mobile**: bearer JWT only (no cookies), JSON, errors via `AppError` subclasses → `{"error": {code, message, details}}`. Never raise bare `HTTPException` in services.
- Path ids: parse with `to_object_id(id, "Thing")` (invalid → 404). Return docs with `serialize_doc` (`_id` → `id`).
- Ownership: every user query filters by `user_id`; other users' resources are **404**, not 403.
- Storage: nested Pydantic → `model_dump(mode="json")`; keep `created_at/updated_at/expires_at/confirm_before` as native `datetime` (sorting, TTL indexes). New collection with lookups/TTL → add to `INDEXES` in `core/database.py`.
- Lists return `Page[T]` with `PageParams`; list projections exclude heavy fields (`plan`).
- New external integration: ABC + `Mock` impl (deterministic) + real impl in `providers/`, a `*_PROVIDER` setting, wiring in `registry.py`, `.env.example` entry, and an `httpx.MockTransport` unit test in `tests/test_providers_unit.py`. Real impls must fail soft for enrichment (log + `[]`) and raise `ProviderError` for user-facing actions.
- LLM output: always `llm.generate_json(prompt, DraftModel)`. Draft models are small/flat and define `mock_example(cls, prompt)`; prompts use `KEY: value` marker lines (see `planner/agents.py:trip_brief`). Never ask the LLM to do arithmetic — compute (see `planner/budget.py`).
- Latency: run independent work with `asyncio.gather`, cache external lookups via `Cache.get_or_set` / `MediaLookup`, time-box enrichment.

## Booking safety (do not weaken)

Chat/voice may search and create `awaiting_confirmation` quotes only. Only `POST /bookings/{id}/confirm` with matching `expected_total` books. Keep: Idempotency-Key, atomic `awaiting_confirmation → processing` transition, refund on supplier failure, `confirm_before` expiry (410).

## Gotchas found in this codebase

- A field named `date` with a default (`date: date | None = None`) breaks at class creation — use the `Date` alias (`from datetime import date as Date`).
- Don't name service methods `list` (shadows the builtin in later annotations) — use `list_trips`, `list_bookings`.
- Regex markers: use `[ \t]*` not `\s*` after `KEY:` (with `re.MULTILINE`, `\s` eats the newline and reads the next line).
- Motor is deprecated — use `pymongo.AsyncMongoClient`.

## Run & test (Windows)

```bash
# MongoDB (service needs admin; run mongod directly if `Start-Service MongoDB` fails)
"/c/Program Files/MongoDB/Server/8.0/bin/mongod.exe" --dbpath <scratch>/mongodata --bind_ip 127.0.0.1

cd backend
venv/Scripts/python.exe -m pytest -q            # all tests; real Mongo db `nomadiq_test`, providers mocked
venv/Scripts/python.exe main.py                  # http://localhost:8000/api/v1/docs
LLM_PROVIDER=mock venv/Scripts/python.exe main.py  # no Ollama needed
```

Tests: `tests/conftest.py` gives `app`, `client` (base `/api/v1`), `auth` (registered user + headers), `db`, `providers`, helpers `register`, `wait_for_trip`, `future(days)`. To fake a provider in one test, swap `providers.<name>` and restore in `finally`. Every new route needs happy-path, validation, auth/ownership tests.

## Clients (same API)

- **Website** `frontend/` (Next.js 16, Tailwind v4): typed client `src/lib/api.ts` (tokens in localStorage, one shared refresh on 401), SSE progress via fetch stream in `src/lib/progress.ts`.
- **Mobile** `mobile/` (Expo SDK 57, Expo Router in `src/app/`): client `src/api/client.ts` (expo-secure-store), polls `/trips/{id}/status`. Install packages with `npx expo install`; read versioned Expo docs, don't trust memory. Keep `react-dom` pinned to the exact `react` version.
- `types.ts`/`format.ts` exist in both apps; change the backend schema → update `docs/API.md` and both copies.
- Design system ("route sheet"): ink `#14213D`, paper `#F3F5F7`, signal yellow `#FFC83D` (only for the route/line), platform teal `#0F766E` (actions), Overpass type, no all-caps labels, small radii. Trips render as transit lines (days = stations).
- Wikimedia thumbnails: only standard widths are served (500/960/1280...); other widths return HTTP 400.
- React effects: never write `useEffect(() => el.scrollIntoView())` as an expression body; scroll methods now return Promises and React will try to call them as cleanup.

## Git

Short commit messages (e.g. `Add hotel search`), **no Co-Authored-By or other attribution lines**. Branch off `main` for larger work; remote is GitHub `origin`.
