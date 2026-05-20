# Clouma Console — Design Spec
**Date:** 2026-05-20  
**Status:** Approved  
**Scope:** Frontend (Next.js) + FastAPI stub — MVP Managed Agent creation & execution

---

## 1. Goal

Users open Clouma Console, type a natural-language instruction (e.g. *"buat agent yang research AI startup trending setiap pagi dan kirim ke Telegram"*), and the system automatically compiles it into an agent spec (YAML/JSON), saves it, and starts execution — with realtime streaming visible in the UI.

This is **not** a chatbot. It is a managed autonomous cloud agent runtime platform.

---

## 2. Stack

### Frontend
| Layer | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Components | shadcn/ui + Radix UI |
| Code editor | Monaco Editor |
| State | Zustand |
| HTTP client | fetch (wrapped in `lib/api.ts`) |
| WebSocket | native WebSocket in `lib/ws.ts` |

### Backend (MVP stub)
| Layer | Choice |
|---|---|
| Framework | FastAPI |
| LLM | OpenAI-compatible API (configurable endpoint) |
| LLM SDK | `openai` Python SDK with custom `base_url` |
| Database | Postgres (agent + session storage) |
| Cache | Redis (session state, event queue) |
| ORM | SQLAlchemy async |

### LLM Configuration (env vars)
```
LLM_BASE_URL=http://localhost:11434/v1   # Ollama / vLLM / Together / Groq / OpenRouter / dll
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
```
Supports any OpenAI-compatible open-source model — no vendor lock-in.

---

## 3. Repo Structure

```
clouma/
├── apps/
│   ├── web/                          # Next.js 14 App Router
│   │   ├── app/
│   │   │   ├── layout.tsx            # root layout
│   │   │   └── (console)/
│   │   │       ├── layout.tsx        # sidebar + step-bar shell
│   │   │       ├── quickstart/
│   │   │       │   └── page.tsx      # main MVP page
│   │   │       ├── agents/
│   │   │       │   ├── page.tsx      # agent list
│   │   │       │   └── [id]/page.tsx # agent detail
│   │   │       └── sessions/
│   │   │           └── page.tsx      # session history + live stream
│   │   ├── components/
│   │   │   ├── sidebar.tsx           # collapsible nav sections
│   │   │   ├── step-bar.tsx          # 4-step top indicator
│   │   │   ├── quickstart-panel.tsx  # prompt textarea + submit
│   │   │   ├── template-browser.tsx  # template grid + search
│   │   │   ├── yaml-editor.tsx       # Monaco, YAML/JSON tabs
│   │   │   └── stream-viewer.tsx     # realtime event display
│   │   ├── lib/
│   │   │   ├── api.ts                # typed fetch wrapper → FastAPI
│   │   │   └── ws.ts                 # WebSocket client + reconnect
│   │   └── store/
│   │       └── agent.ts              # Zustand: draft, session, events
│   └── api/                          # FastAPI stub
│       ├── main.py
│       ├── routers/
│       │   ├── agents.py             # CRUD + compile endpoint
│       │   └── sessions.py           # session start + WS stream
│       ├── services/
│       │   └── compiler.py           # prompt → YAML via LLM
│       ├── models/
│       │   ├── agent.py              # SQLAlchemy Agent model
│       │   └── session.py            # SQLAlchemy Session model
│       └── schemas/
│           ├── agent.py              # Pydantic schemas
│           └── session.py
├── docker-compose.yml                # Postgres + Redis for dev
└── docs/
    └── superpowers/specs/
        └── 2026-05-20-clouma-console-design.md
```

---

## 4. UI Layout

### Sidebar (fixed, collapsible sections)
```
Claude Console  [logo]
─────────────────────
[Default ▾]           ← workspace dropdown
─────────────────────
⊡ Dashboard
🔨 Build ▾
   Workbench / Files / Skills / Batches
🤖 Managed Agents ▾  ← active section
   Quickstart  ← active page
   Agents
   Sessions
   Environments
   Credential vaults
   Memory stores
📊 Analytics ▸
⚡ Claude Code ▸
⚙️ Manage ▸
─────────────────────
📖 Documentation
🕐 Credits  $0.00
👤 razor  Admin · org ▾
```

### Top Step Bar (Quickstart only)
```
Quickstart  |  ① Create agent POST /v1/agents  |  ② Configure environment  |  ③ Start session  |  ④ Integrate
```
Steps 2–4 unlock setelah step sebelumnya selesai.

### Quickstart Page — Split Panel
```
┌─────────────────────────┬──────────────────────────────────┐
│                         │  Browse templates / YAML editor  │
│  What do you want       │  ┌─────────────────────────────┐ │
│  to build?              │  │ Search templates...          │ │
│                         │  ├─────────────┬───────────────┤ │
│  (centered, empty       │  │ Blank agent │ Deep researchr│ │
│   state)                │  │ Support     │ Incident cmd  │ │
│                         │  │ Contract    │ Data analyst  │ │
│                         │  └─────────────┴───────────────┘ │
│                         │                                  │
│  ┌─────────────────┐    │  After compile:                  │
│  │ Describe your   │    │  YAML/JSON tabs + Monaco editor  │
│  │ agent...      ↑ │    │  "Use this template" button      │
│  └─────────────────┘    │                                  │
└─────────────────────────┴──────────────────────────────────┘
```

---

## 5. Agent Config Format

Agent config disimpan dalam dua format yang saling konversi:

**YAML** (ditampilkan di editor — human-readable):
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

mcp_servers:
  - name: telegram
    type: url
    url: https://mcp.telegram.example/mcp
```

**JSON** (disimpan di Postgres — dipakai runtime):
```json
{
  "name": "ai-startup-researcher",
  "model": "llama3.2",
  "schedule": "0 8 * * *",
  "tools": ["web_search", "telegram_send", "memory_store"],
  "memory": { "type": "episodic", "backend": "qdrant" },
  "runtime": { "sandbox": "browser", "timeout": 300 }
}
```

Konversi YAML ↔ JSON terjadi di frontend (`yaml` npm package) dan backend (`pyyaml`).

---

## 6. API Contract

### REST Endpoints

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/v1/agents/compile` | `{ prompt: string }` | `{ yaml: string, tools: string[], schedule: string }` (streaming SSE) |
| `POST` | `/v1/agents` | `{ yaml: string, name: string }` | `{ id, status: "created" }` |
| `GET` | `/v1/agents` | — | `{ agents: Agent[] }` |
| `GET` | `/v1/agents/{id}` | — | `Agent` |
| `DELETE` | `/v1/agents/{id}` | — | `{ ok: true }` |
| `POST` | `/v1/sessions` | `{ agent_id: string }` | `{ session_id, status: "running" }` |
| `GET` | `/v1/sessions` | — | `{ sessions: Session[] }` |

### WebSocket

```
WS /v1/sessions/{session_id}/stream
```

**Events (JSON per line):**
```json
{ "type": "token",       "content": "Searching for AI startups..." }
{ "type": "tool_call",   "tool": "web_search", "input": "trending AI startups May 2026" }
{ "type": "tool_result", "tool": "web_search", "output": "1. Company A..." }
{ "type": "checkpoint",  "step": 2, "state": "searching" }
{ "type": "status",      "status": "running" | "waiting" | "completed" | "failed" }
{ "type": "error",       "message": "Tool timeout" }
```

---

## 7. Compiler Service (LLM)

`apps/api/services/compiler.py` adalah satu-satunya tempat LLM dipanggil:

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url=settings.LLM_BASE_URL,
    api_key=settings.LLM_API_KEY,
)

SYSTEM_PROMPT = """
You are an agent compiler. Given a natural language instruction, output a valid YAML agent spec.
The YAML must include: name, description, model, tools[], memory, runtime, schedule (cron or null).
Output ONLY the YAML. No explanation. No markdown fences.
"""

async def compile_prompt_to_yaml(prompt: str) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

Output di-stream ke frontend via SSE sehingga YAML muncul token-by-token di editor.

---

## 8. Zustand State

```ts
interface AgentStore {
  // Draft (saat Quickstart)
  prompt: string
  yaml: string
  agentName: string
  activeTab: "yaml" | "json"

  // Created agent
  agentId: string | null

  // Session
  sessionId: string | null
  streamEvents: StreamEvent[]
  sessionStatus: "idle" | "running" | "completed" | "failed"

  // UI
  currentStep: 1 | 2 | 3 | 4
  isCompiling: boolean
}
```

---

## 9. MVP Implementation Order

1. **Project scaffold** — monorepo setup, Next.js + FastAPI skeleton, docker-compose
2. **Sidebar + layout** — collapsible nav, routing, shell
3. **Quickstart page** — split panel, textarea, template browser (static templates)
4. **Compiler endpoint** — FastAPI `POST /v1/agents/compile` → LLM → SSE stream
5. **YAML editor** — Monaco, YAML/JSON tabs, streaming display
6. **Create agent** — `POST /v1/agents`, Postgres persistence
7. **Start session + WebSocket** — session creation, WS connection, stream viewer
8. **Agent list page** — `/agents` table
9. **Step bar** — unlock steps progressively
10. **Polish** — loading states, error handling, empty states

---

## 10. Out of Scope (MVP)

- Temporal workflow orchestration
- Qdrant vector memory
- Kubernetes deployment
- Scheduler / cron execution
- Multi-agent (supervisor/worker)
- Authentication / billing
