# Clouma Console

Managed autonomous cloud agent runtime platform. Users describe what they want in natural language — Clouma compiles it into an agent spec, creates the agent, and streams execution in realtime.

![Dark-themed console UI with sidebar, YAML editor, and stream viewer](.github/preview.png)

---

## What it does

1. **Type a prompt** — *"research trending AI startups every morning and send a summary to Telegram"*
2. **Agent spec generated** — LLM compiles prompt → YAML spec (streamed token-by-token into Monaco editor)
3. **Create & run** — agent saved to Postgres, session started, execution events streamed via WebSocket

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind v4, shadcn/ui, Zustand, Monaco Editor |
| Backend | FastAPI, SQLAlchemy async, Postgres, Redis |
| LLM | Any OpenAI-compatible model (Ollama, vLLM, Together, Groq, OpenRouter) |
| Streaming | SSE (compile), WebSocket (execution) |

---

## Getting started

### Prerequisites

- Docker Desktop
- Python 3.10+
- Node.js 18+
- An OpenAI-compatible LLM endpoint (e.g. [Ollama](https://ollama.ai))

### 1. Clone & configure

```bash
git clone https://github.com/anasrudin/clouma.git
cd clouma
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql+asyncpg://clouma:clouma@localhost:5432/clouma
REDIS_URL=redis://localhost:6379

# Point to your LLM — examples:
LLM_BASE_URL=http://localhost:11434/v1   # Ollama
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
```

### 2. Start infrastructure

```bash
docker compose up -d
```

### 3. Start backend

```bash
cd apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API runs at `http://localhost:8000` — verify: `curl http://localhost:8000/health`

### 4. Start frontend

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) → redirects to Quickstart.

---

## Project structure

```
clouma/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # app entry, CORS, router registration
│   │   ├── config.py           # env-based settings (pydantic-settings)
│   │   ├── database.py         # async SQLAlchemy engine
│   │   ├── models/             # Agent, Session ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── agents.py       # POST /v1/agents/compile (SSE), CRUD
│   │   │   └── sessions.py     # POST /v1/sessions, WS stream
│   │   └── services/
│   │       └── compiler.py     # prompt → YAML via OpenAI-compatible LLM
│   └── web/                    # Next.js 16 frontend
│       ├── app/
│       │   └── (console)/
│       │       ├── layout.tsx          # sidebar + step-bar shell
│       │       ├── quickstart/page.tsx # main MVP page
│       │       ├── agents/page.tsx     # agent list
│       │       └── sessions/page.tsx   # session history
│       ├── components/
│       │   ├── sidebar.tsx             # collapsible nav
│       │   ├── step-bar.tsx            # 4-step progress indicator
│       │   ├── quickstart-panel.tsx    # prompt textarea
│       │   ├── template-browser.tsx    # 6 built-in templates
│       │   ├── yaml-editor.tsx         # Monaco YAML/JSON editor
│       │   └── stream-viewer.tsx       # realtime execution stream
│       ├── lib/
│       │   ├── api.ts                  # fetch wrapper (SSE + REST)
│       │   └── ws.ts                   # WebSocket client
│       └── store/agent.ts             # Zustand state
├── docker-compose.yml          # Postgres + Redis
└── .env.example
```

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/agents/compile` | Compile prompt → YAML (SSE stream) |
| `POST` | `/v1/agents` | Create agent from YAML |
| `GET` | `/v1/agents` | List all agents |
| `GET` | `/v1/agents/{id}` | Get agent by ID |
| `DELETE` | `/v1/agents/{id}` | Delete agent |
| `POST` | `/v1/sessions` | Start execution session |
| `GET` | `/v1/sessions` | List sessions |
| `WS` | `/v1/sessions/{id}/stream` | Stream execution events |

### WebSocket event types

```json
{ "type": "token",       "content": "..." }
{ "type": "tool_call",   "tool": "web_search", "input": "..." }
{ "type": "tool_result", "tool": "web_search", "output": "..." }
{ "type": "checkpoint",  "step": 1, "state": "search_complete" }
{ "type": "status",      "status": "running|completed|failed" }
```

---

## Agent YAML spec

```yaml
name: ai-startup-researcher
description: Researches trending AI startups every morning
model: llama3.2
schedule: "0 8 * * *"

tools:
  - web_search
  - telegram_send
  - memory_store

memory:
  type: episodic
  backend: qdrant

runtime:
  sandbox: browser
  timeout: 300
```

---

## Roadmap

- [ ] Temporal workflow orchestration
- [ ] Qdrant vector memory
- [ ] Real tool execution (web_search, telegram_send, etc.)
- [ ] Cron scheduler for autonomous agents
- [ ] Multi-agent supervisor/worker architecture
- [ ] Authentication & billing
- [ ] Kubernetes deployment
