# 🌍 NomadIQ — AI-Powered Travel Itinerary Generator

> **Plan your dream trip in seconds.** NomadIQ uses a team of specialized AI agents to research destinations, find hotels, discover restaurants, and craft a complete day-by-day itinerary — all for free.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)

---

## ✨ Features

- 🤖 **Multi-Agent AI** — 5 specialized agents collaborate in parallel to produce comprehensive plans
- 📅 **Day-by-Day Itineraries** — Morning, afternoon & evening activities with realistic timing
- 🏨 **Hotel Recommendations** — Curated stays matched to your budget and style
- 🍽️ **Dining Suggestions** — Local restaurants and hidden culinary gems
- 💰 **Budget Breakdown** — Transparent cost estimates across the entire trip
- 💬 **AI Chat to Modify** — Ask the AI to refine any part of your plan in plain English
- 🔄 **Real-time Generation** — Watch your plan build live with async background processing
- 🔐 **User Authentication** — Sign up and save/manage all your trips

---

## 🏗️ Architecture

NomadIQ is a full-stack application with a clear separation between the AI backend and the web frontend.

```
ai_travel_planner_agent_team/
├── backend/                       # FastAPI backend (shared by web + mobile)
│   ├── app/
│   │   ├── core/                  # config, MongoDB, JWT security, cache, rate limit, jobs, errors
│   │   ├── common/                # shared Pydantic schemas (money, media, offers, FX)
│   │   ├── providers/             # swappable integrations: LLM, Duffel, LiteAPI, images,
│   │   │                          #   videos, weather, speech, payments (+ mocks)
│   │   ├── modules/               # feature modules: router + schemas + service each
│   │   │   ├── auth/ users/ trips/ planner/ search/
│   │   │   └── bookings/ explore/ assistant/ meta/
│   │   └── main.py                # app factory
│   ├── tests/                     # 76 tests (real MongoDB, mocked providers)
│   ├── main.py                    # uvicorn entry point
│   └── requirements.txt
│
└── frontend/                      # Next.js 16 + TypeScript frontend
    └── src/
        ├── app/
        │   ├── page.tsx           # Landing / home page
        │   ├── plan/              # Trip planning form & live results
        │   ├── plans/             # Saved trips dashboard
        │   ├── login/             # Authentication pages
        │   └── signup/
        ├── components/            # Reusable UI components (shadcn/ui)
        └── lib/                   # API helpers, utilities
```

### Agent Team Overview

| Agent | Role |
|---|---|
| 🏛️ **Destination Agent** | Researches top attractions, landmarks, and local experiences |
| 🏨 **Hotel Agent** | Finds accommodations matching your budget and preferences |
| 🍽️ **Dining Agent** | Discovers restaurants, local cuisine, and hidden gems |
| 💰 **Budget Agent** | Estimates costs and produces a transparent budget breakdown |
| 📅 **Itinerary Agent** | Synthesizes all agent outputs into a cohesive day-by-day plan |

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10 or newer
- **Node.js** 18 or newer & npm
- **Ollama** (for free local AI) _or_ a **Google Gemini API key** (free tier)

---

### 1. Clone the Repository

```bash
git clone https://github.com/S07singh/NomadIQ-AI-powered-travel-itinerary-generator.git
cd NomadIQ-AI-powered-travel-itinerary-generator
```

---

### 2. Backend Setup

```bash
cd backend

# Create & activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your chosen LLM provider:

```env
# ── Option A: Ollama (local, 100% free — recommended) ──────────────────
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# ── Option B: Google Gemini (cloud, free tier) ──────────────────────────
# LLM_PROVIDER=gemini
# GOOGLE_API_KEY=your_google_api_key_here
# GEMINI_MODEL=gemini-2.0-flash
```

#### (Option A) Install & Run Ollama

```bash
# Download from https://ollama.com/download, then pull a model:
ollama pull llama3.1
```

#### Start MongoDB

Local: install MongoDB Community and run `mongod` (default `mongodb://127.0.0.1:27017`).
Production: set `MONGODB_URI` to your MongoDB Atlas connection string.

#### Start the Backend

```bash
python main.py
```

The API will be live at **http://localhost:8000/api/v1**
Interactive API docs: **http://localhost:8000/api/v1/docs**

#### Run the Tests

```bash
pip install -r requirements-dev.txt
pytest -q          # needs a local mongod; uses the `nomadiq_test` database
```

---

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install
```

#### Configure Frontend Environment

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXTAUTH_URL=http://localhost:3000
```

#### Start the Frontend

```bash
npm run dev
```

The app will be available at **http://localhost:3000**

---

## 🔌 API Reference

All endpoints live under `/api/v1` and are shared by the website and the mobile app.
Full reference with every route and Pydantic model: **[docs/API.md](./docs/API.md)**. Product roadmap: **[docs/PRODUCT_PLAN.md](./docs/PRODUCT_PLAN.md)**.

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/password/change` |
| Users | `GET/PATCH/DELETE /users/me`, saved travelers, push devices |
| Trips | `POST/GET /trips`, `GET/PATCH/DELETE /trips/{id}`, `/generate`, `/status`, `/events` (SSE), `/chat`, `/share` |
| Search | `POST /search/flights`, `/hotels`, `/trains`, `/buses`, `/activities`, `GET /search/airports` |
| Bookings | `POST /bookings` → `POST /bookings/{id}/confirm` → `/cancel` |
| Explore | `GET /explore/destination`, `/places`, `/images`, `/videos`, `/weather` |
| Assistant & Voice | `POST /assistant/messages`, `POST /voice/transcribe`, `POST /voice/assistant` |

### Example: plan a trip

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/register -H "Content-Type: application/json"   -d '{"email":"me@example.com","password":"secret123","name":"Me"}' | jq -r .tokens.access_token)

curl -X POST localhost:8000/api/v1/trips -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   -d '{"destination":"Goa, India","start_date":"2026-12-10","duration_days":4,"budget":{"amount":60000,"currency":"INR"}}'

curl -N localhost:8000/api/v1/trips/<id>/events -H "Authorization: Bearer $TOKEN"   # live progress
```

> The Next.js frontend still calls the v1 (`/api/plan/...`) endpoints and needs migrating to `/api/v1`.

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **FastAPI** | ≥ 0.115 | High-performance async REST API |
| **Uvicorn** | ≥ 0.34 | ASGI server |
| **Pydantic** | v2 | Data validation & serialization |
| **MongoDB + PyMongo Async** | 8.x / ≥ 4.13 | Database (local → Atlas) |
| **PyJWT + bcrypt** | — | Token auth for web & mobile |
| **Duffel / LiteAPI** | — | Flight & hotel inventory (mock providers until keys) |
| **Open-Meteo / Wikipedia / YouTube** | — | Weather, geocoding, photos, videos |
| **Loguru** | ≥ 0.7 | Structured logging |
| **httpx** | ≥ 0.28 | Async HTTP client |
| **Ollama / Google Gemini** | — | LLM inference providers |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 16 | React framework with App Router |
| **TypeScript** | ^5 | Type-safe JavaScript |
| **Tailwind CSS** | v4 | Utility-first styling |
| **shadcn/ui** | ^4 | Accessible UI component library |
| **NextAuth** | v5 beta | Authentication |
| **Prisma** | ^6 | ORM for user/session data |
| **Lucide React** | ^0.577 | Icon library |
| **react-markdown** | ^10 | Render AI-generated markdown |

---

## ⚙️ Configuration

### LLM Provider Options

NomadIQ supports two LLM providers, switchable via the `LLM_PROVIDER` environment variable in `backend/.env`:

| Provider | Cost | Setup | Best For |
|---|---|---|---|
| **Ollama** *(default)* | Free, runs locally | Install Ollama + pull a model | Privacy, offline use, no API key |
| **Google Gemini** | Free tier available | Get key at [aistudio.google.com](https://aistudio.google.com/apikey) | Cloud, no local GPU needed |

### Recommended Models

| Provider | Recommended Models |
|---|---|
| Ollama | `llama3.1`, `mistral`, `gemma2` |
| Gemini | `gemini-2.0-flash`, `gemini-1.5-flash` |

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Commit your changes**: `git commit -m 'Add your feature'`
4. **Push to the branch**: `git push origin feature/your-feature`
5. **Open a Pull Request**

Please keep PRs focused — one feature or fix per PR.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgements

- [Ollama](https://ollama.com) — for making local LLMs accessible to everyone
- [Google AI Studio](https://aistudio.google.com) — for the free Gemini API tier
- [shadcn/ui](https://ui.shadcn.com) — for the beautiful, accessible component system
- [FastAPI](https://fastapi.tiangolo.com) — for the incredible async Python framework

---

<div align="center">
  <strong>Built with ❤️ by <a href="https://github.com/S07singh">S07singh</a></strong><br/>
  <em>Happy travels! 🌏✈️</em>
</div>
