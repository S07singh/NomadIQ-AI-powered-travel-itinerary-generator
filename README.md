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
├── backend/                       # FastAPI Python backend
│   ├── agents/
│   │   ├── destination_agent.py   # Researches attractions & landmarks
│   │   ├── hotel_agent.py         # Finds and recommends accommodations
│   │   ├── dining_agent.py        # Discovers restaurants & dining
│   │   ├── budget_agent.py        # Calculates and breaks down costs
│   │   └── itinerary_agent.py     # Compiles the final day-by-day plan
│   ├── api/
│   │   ├── app.py                 # FastAPI app factory
│   │   └── routes.py              # All REST API endpoints
│   ├── config/
│   │   ├── llm.py                 # Unified LLM provider (Ollama / Gemini)
│   │   └── logger.py              # Loguru logging setup
│   ├── models/
│   │   └── schemas.py             # Pydantic request/response models
│   ├── services/
│   │   ├── plan_service.py        # Orchestrates multi-agent plan generation
│   │   └── db_service.py          # SQLite persistence layer (aiosqlite)
│   ├── main.py                    # Uvicorn entry point
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

#### Start the Backend

```bash
python main.py
```

The API will be live at **http://localhost:8000**  
Interactive API docs: **http://localhost:8000/docs**

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/plan/trigger` | Start async trip plan generation |
| `GET` | `/api/plan/{id}` | Poll plan status & retrieve results |
| `GET` | `/api/plans` | List all saved trip plans |
| `POST` | `/api/chat` | Modify an existing itinerary via AI chat |
| `GET` | `/api/chat/{id}` | Retrieve chat history for a plan |

### Example: Trigger a Plan

```bash
curl -X POST http://localhost:8000/api/plan/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "travel_plan": {
      "destination": "Tokyo, Japan",
      "duration_days": 7,
      "budget": "moderate",
      "travel_style": "culture and food"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Trip plan generation started",
  "trip_plan_id": "abc123..."
}
```

Then poll `GET /api/plan/{trip_plan_id}` every few seconds until `status` is `"completed"`.

### Example: Chat to Modify

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "trip_plan_id": "abc123...",
    "message": "Make day 2 more adventurous and add local street food spots"
  }'
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **FastAPI** | ≥ 0.115 | High-performance async REST API |
| **Uvicorn** | ≥ 0.34 | ASGI server |
| **Pydantic** | v2 | Data validation & serialization |
| **aiosqlite** | ≥ 0.20 | Async SQLite database |
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
