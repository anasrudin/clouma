# Clouma Console MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Clouma Console — a dark-themed SaaS UI where users type a natural-language prompt, the system compiles it into a YAML agent spec via an OpenAI-compatible LLM, saves it, and streams execution events in realtime.

**Architecture:** Monorepo with `apps/web` (Next.js 14 App Router) and `apps/api` (FastAPI). Frontend calls FastAPI REST + SSE for YAML compilation, then connects via WebSocket for session streaming. State managed with Zustand; agent config stored as YAML in editor and JSON in Postgres.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, Zustand, Monaco Editor, FastAPI, SQLAlchemy async, Postgres, Redis, `openai` Python SDK (custom base_url for any OpenAI-compatible model)

---

## File Map

```
clouma/
├── apps/
│   ├── web/                               # Next.js 14
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── tsconfig.json
│   │   ├── components.json                # shadcn config
│   │   ├── app/
│   │   │   ├── globals.css
│   │   │   ├── layout.tsx                 # root html shell
│   │   │   └── (console)/
│   │   │       ├── layout.tsx             # sidebar + step-bar shell
│   │   │       ├── quickstart/page.tsx    # main MVP page
│   │   │       ├── agents/page.tsx        # agent list
│   │   │       └── sessions/page.tsx      # session history
│   │   ├── components/
│   │   │   ├── sidebar.tsx                # collapsible nav sections
│   │   │   ├── step-bar.tsx               # 4-step top indicator
│   │   │   ├── quickstart-panel.tsx       # left panel textarea
│   │   │   ├── template-browser.tsx       # right panel template grid
│   │   │   ├── yaml-editor.tsx            # Monaco YAML/JSON tabs
│   │   │   └── stream-viewer.tsx          # realtime WS event display
│   │   ├── lib/
│   │   │   ├── api.ts                     # typed fetch → FastAPI
│   │   │   └── ws.ts                      # WebSocket client
│   │   └── store/
│   │       └── agent.ts                   # Zustand store
│   └── api/                               # FastAPI
│       ├── requirements.txt
│       ├── main.py
│       ├── config.py                      # env vars (LLM, DB, Redis)
│       ├── database.py                    # async SQLAlchemy engine
│       ├── routers/
│       │   ├── agents.py                  # compile + CRUD
│       │   └── sessions.py                # create + WS stream
│       ├── services/
│       │   └── compiler.py                # prompt → YAML via LLM (SSE)
│       ├── models/
│       │   ├── agent.py                   # SQLAlchemy Agent table
│       │   └── session.py                 # SQLAlchemy Session table
│       └── schemas/
│           ├── agent.py                   # Pydantic agent schemas
│           └── session.py                 # Pydantic session schemas
├── docker-compose.yml                     # Postgres + Redis
└── .env.example
```

---

## Task 1: Monorepo Scaffold + Docker

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `apps/api/requirements.txt`
- Create: `apps/api/config.py`

- [ ] **Step 1: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: clouma
      POSTGRES_USER: clouma
      POSTGRES_PASSWORD: clouma
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 2: Create .env.example**

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://clouma:clouma@localhost:5432/clouma
REDIS_URL=redis://localhost:6379

LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.2
LLM_API_KEY=ollama
```

Copy to `.env`: `cp .env.example .env`

- [ ] **Step 3: Create apps/api/requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic-settings==2.2.1
openai==1.30.0
pyyaml==6.0.1
python-dotenv==1.0.1
websockets==12.0
redis==5.0.4
httpx==0.27.0
```

Install: `cd apps/api && pip install -r requirements.txt`

- [ ] **Step 4: Create apps/api/config.py**

```python
# apps/api/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    llm_base_url: str
    llm_model: str = "llama3.2"
    llm_api_key: str = "ollama"

    class Config:
        env_file = ".env"

settings = Settings()
```

- [ ] **Step 5: Start services**

```bash
docker compose up -d
docker compose ps
# Expected: postgres and redis both "running"
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example apps/api/requirements.txt apps/api/config.py
git commit -m "chore: monorepo scaffold, docker services, api config"
```

---

## Task 2: FastAPI Core + Database

**Files:**
- Create: `apps/api/database.py`
- Create: `apps/api/models/agent.py`
- Create: `apps/api/models/session.py`
- Create: `apps/api/main.py`

- [ ] **Step 1: Create apps/api/database.py**

```python
# apps/api/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Create apps/api/models/agent.py**

```python
# apps/api/models/agent.py
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    yaml_config: Mapped[str] = mapped_column(Text, nullable=False)
    json_config: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 3: Create apps/api/models/session.py**

```python
# apps/api/models/session.py
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Create apps/api/main.py (without router imports — added in Task 3)**

```python
# apps/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield

app = FastAPI(title="Clouma API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4b: Create package __init__.py files**

```bash
touch apps/api/models/__init__.py
touch apps/api/schemas/__init__.py
```

- [ ] **Step 5: Start API and verify health**

```bash
cd apps/api
uvicorn main:app --reload --port 8000
# In another terminal:
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/database.py apps/api/models/ apps/api/main.py
git commit -m "feat(api): fastapi core, db engine, agent + session models"
```

---

## Task 3: Pydantic Schemas + Agent CRUD Router

**Files:**
- Create: `apps/api/schemas/agent.py`
- Create: `apps/api/schemas/session.py`
- Create: `apps/api/routers/agents.py`

- [ ] **Step 1: Create apps/api/schemas/agent.py**

```python
# apps/api/schemas/agent.py
from pydantic import BaseModel
from datetime import datetime

class AgentCreate(BaseModel):
    name: str
    yaml_config: str

class AgentOut(BaseModel):
    id: str
    name: str
    yaml_config: str
    json_config: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class CompileRequest(BaseModel):
    prompt: str
```

- [ ] **Step 2: Create apps/api/schemas/session.py**

```python
# apps/api/schemas/session.py
from pydantic import BaseModel
from datetime import datetime

class SessionCreate(BaseModel):
    agent_id: str

class SessionOut(BaseModel):
    id: str
    agent_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Create apps/api/routers/agents.py**

```python
# apps/api/routers/agents.py
import json
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.agent import Agent
from ..schemas.agent import AgentCreate, AgentOut, CompileRequest
from ..services.compiler import compile_prompt_to_yaml

router = APIRouter()

@router.post("/agents/compile")
async def compile_agent(req: CompileRequest):
    async def generate():
        async for token in compile_prompt_to_yaml(req.prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.post("/agents", response_model=AgentOut)
async def create_agent(req: AgentCreate, db: AsyncSession = Depends(get_db)):
    try:
        parsed = yaml.safe_load(req.yaml_config)
        json_config = json.dumps(parsed)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid YAML")

    agent = Agent(name=req.name, yaml_config=req.yaml_config, json_config=json_config)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent

@router.get("/agents", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()

@router.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Create apps/api/routers/__init__.py**

```python
# apps/api/routers/__init__.py
```

- [ ] **Step 4c: Update apps/api/main.py to register routers**

Add these lines to `main.py` after the middleware block:

```python
# add after app.add_middleware(...)
from .routers import agents, sessions
app.include_router(agents.router, prefix="/v1")
app.include_router(sessions.router, prefix="/v1")
```

- [ ] **Step 5: Test agent list endpoint**

```bash
# Restart uvicorn after updating main.py
curl http://localhost:8000/v1/agents
# Expected: []
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/schemas/ apps/api/routers/
git commit -m "feat(api): agent schemas, CRUD router, SSE compile endpoint"
```

---

## Task 4: Compiler Service (LLM → YAML via SSE)

**Files:**
- Create: `apps/api/services/__init__.py`
- Create: `apps/api/services/compiler.py`

- [ ] **Step 1: Create apps/api/services/compiler.py**

```python
# apps/api/services/compiler.py
from typing import AsyncIterator
from openai import AsyncOpenAI
from ..config import settings

client = AsyncOpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)

SYSTEM_PROMPT = """You are an agent compiler for the Clouma platform.
Given a natural language instruction from the user, output a valid YAML agent spec.

The YAML must include these fields:
- name: (slug, lowercase, hyphens)
- description: (one line)
- model: (use the model name from the instruction, or default to "llama3.2")
- schedule: (cron string like "0 8 * * *", or null if not scheduled)
- tools: (list of tool names inferred from the task)
- memory:
    type: episodic
    backend: qdrant
- runtime:
    sandbox: browser
    timeout: 300

Available tools: web_search, telegram_send, slack_send, email_send, memory_store, file_read, file_write, code_exec, browser_navigate, api_call

Output ONLY valid YAML. No explanation. No markdown code fences. No extra text."""

async def compile_prompt_to_yaml(prompt: str) -> AsyncIterator[str]:
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        temperature=0.2,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
```

- [ ] **Step 2: Create apps/api/services/__init__.py**

```python
# apps/api/services/__init__.py
```

- [ ] **Step 3: Test compile endpoint (requires LLM running)**

```bash
curl -X POST http://localhost:8000/v1/agents/compile \
  -H "Content-Type: application/json" \
  -d '{"prompt": "buat agent yang kirim ringkasan berita AI setiap pagi ke Telegram"}' \
  --no-buffer
# Expected: SSE stream of YAML tokens, ending with data: [DONE]
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/services/
git commit -m "feat(api): LLM compiler service, SSE YAML streaming"
```

---

## Task 5: Session Router + WebSocket Streaming

**Files:**
- Create: `apps/api/routers/sessions.py`

- [ ] **Step 1: Create apps/api/routers/sessions.py**

```python
# apps/api/routers/sessions.py
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.session import Session
from ..models.agent import Agent
from ..schemas.session import SessionCreate, SessionOut

router = APIRouter()

@router.post("/sessions", response_model=SessionOut)
async def create_session(req: SessionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    session = Session(agent_id=req.agent_id, status="running")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    return result.scalars().all()

@router.websocket("/sessions/{session_id}/stream")
async def stream_session(session_id: str, websocket: WebSocket):
    await websocket.accept()
    try:
        # Simulate agent execution events for MVP
        events = [
            {"type": "status", "status": "running"},
            {"type": "token", "content": "Starting agent execution..."},
            {"type": "tool_call", "tool": "web_search", "input": "trending AI startups 2026"},
            {"type": "token", "content": "Searching the web..."},
            {"type": "tool_result", "tool": "web_search", "output": "Found 10 results about AI startups."},
            {"type": "token", "content": "Compiling summary..."},
            {"type": "checkpoint", "step": 1, "state": "search_complete"},
            {"type": "tool_call", "tool": "telegram_send", "input": "Summary: Top AI startups this week..."},
            {"type": "tool_result", "tool": "telegram_send", "output": "Message sent successfully."},
            {"type": "status", "status": "completed"},
        ]
        for event in events:
            await websocket.send_text(json.dumps(event))
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 2: Verify WebSocket endpoint compiles without error**

```bash
# Restart API server and check no import errors
uvicorn main:app --reload --port 8000
# Expected: server starts, no errors in output
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/routers/sessions.py
git commit -m "feat(api): session CRUD, websocket streaming (simulated MVP)"
```

---

## Task 6: Next.js Scaffold + shadcn/ui

**Files:**
- Create: `apps/web/` (full Next.js project)

- [ ] **Step 1: Scaffold Next.js app**

```bash
cd apps
npx create-next-app@latest web \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir=false \
  --import-alias="@/*"
cd web
```

- [ ] **Step 2: Install shadcn/ui**

```bash
npx shadcn@latest init
# When prompted:
# Style: Default
# Base color: Slate
# CSS variables: Yes
```

- [ ] **Step 3: Add required shadcn components**

```bash
npx shadcn@latest add button input scroll-area separator badge tooltip
```

- [ ] **Step 4: Install additional dependencies**

```bash
npm install zustand yaml @monaco-editor/react
npm install -D @types/node
```

- [ ] **Step 5: Update tailwind.config.ts to add dark mode**

Open `tailwind.config.ts` and verify `darkMode: ["class"]` is present (shadcn adds it). If not, add it:

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss"
const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
  ],
  plugins: [require("tailwindcss-animate")],
}
export default config
```

- [ ] **Step 6: Replace app/globals.css with dark theme base**

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 8%;
    --foreground: 0 0% 88%;
    --card: 0 0% 10%;
    --card-foreground: 0 0% 88%;
    --border: 0 0% 16%;
    --input: 0 0% 12%;
    --primary: 263 70% 58%;
    --primary-foreground: 0 0% 100%;
    --muted: 0 0% 14%;
    --muted-foreground: 0 0% 50%;
    --accent: 263 70% 58%;
    --accent-foreground: 0 0% 100%;
    --radius: 0.5rem;
  }
}

* { box-sizing: border-box; }
html, body { height: 100%; background: hsl(var(--background)); }
```

- [ ] **Step 7: Update app/layout.tsx**

```tsx
// app/layout.tsx
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Clouma Console",
  description: "Managed autonomous agent platform",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
```

- [ ] **Step 8: Run dev server and verify it starts**

```bash
npm run dev
# Open http://localhost:3000
# Expected: Next.js default page loads without errors
```

- [ ] **Step 9: Commit**

```bash
git add apps/web/
git commit -m "chore(web): next.js scaffold, shadcn/ui, dark theme globals"
```

---

## Task 7: Zustand Store + API/WS Clients

**Files:**
- Create: `apps/web/store/agent.ts`
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/lib/ws.ts`

- [ ] **Step 1: Create apps/web/store/agent.ts**

```ts
// store/agent.ts
import { create } from "zustand"

export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; input: string }
  | { type: "tool_result"; tool: string; output: string }
  | { type: "checkpoint"; step: number; state: string }
  | { type: "status"; status: "running" | "waiting" | "completed" | "failed" }
  | { type: "error"; message: string }

export interface AgentStore {
  // Draft
  prompt: string
  yaml: string
  agentName: string
  activeTab: "yaml" | "json"
  isCompiling: boolean

  // Persisted
  agentId: string | null

  // Session
  sessionId: string | null
  streamEvents: StreamEvent[]
  sessionStatus: "idle" | "running" | "completed" | "failed"

  // Step indicator
  currentStep: 1 | 2 | 3 | 4

  // Actions
  setPrompt: (p: string) => void
  setYaml: (y: string) => void
  setAgentName: (n: string) => void
  setActiveTab: (t: "yaml" | "json") => void
  setIsCompiling: (v: boolean) => void
  setAgentId: (id: string) => void
  setSessionId: (id: string) => void
  addStreamEvent: (e: StreamEvent) => void
  clearStreamEvents: () => void
  setSessionStatus: (s: "idle" | "running" | "completed" | "failed") => void
  setCurrentStep: (s: 1 | 2 | 3 | 4) => void
  reset: () => void
}

const initialState = {
  prompt: "",
  yaml: "",
  agentName: "",
  activeTab: "yaml" as const,
  isCompiling: false,
  agentId: null,
  sessionId: null,
  streamEvents: [],
  sessionStatus: "idle" as const,
  currentStep: 1 as const,
}

export const useAgentStore = create<AgentStore>((set) => ({
  ...initialState,
  setPrompt: (prompt) => set({ prompt }),
  setYaml: (yaml) => set({ yaml }),
  setAgentName: (agentName) => set({ agentName }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setIsCompiling: (isCompiling) => set({ isCompiling }),
  setAgentId: (agentId) => set({ agentId, currentStep: 2 }),
  setSessionId: (sessionId) => set({ sessionId, currentStep: 3 }),
  addStreamEvent: (e) => set((s) => ({ streamEvents: [...s.streamEvents, e] })),
  clearStreamEvents: () => set({ streamEvents: [] }),
  setSessionStatus: (sessionStatus) => set({ sessionStatus }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  reset: () => set(initialState),
}))
```

- [ ] **Step 2: Create apps/web/lib/api.ts**

```ts
// lib/api.ts
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function compileAgent(
  prompt: string,
  onToken: (token: string) => void
): Promise<void> {
  const res = await fetch(`${API}/v1/agents/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  })
  if (!res.body) throw new Error("No response body")
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const lines = decoder.decode(value).split("\n")
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue
      const data = line.slice(6).trim()
      if (data === "[DONE]") return
      try {
        const parsed = JSON.parse(data)
        if (parsed.token) onToken(parsed.token)
      } catch {}
    }
  }
}

export async function createAgent(name: string, yaml_config: string) {
  const res = await fetch(`${API}/v1/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, yaml_config }),
  })
  if (!res.ok) throw new Error("Failed to create agent")
  return res.json()
}

export async function listAgents() {
  const res = await fetch(`${API}/v1/agents`)
  if (!res.ok) throw new Error("Failed to list agents")
  return res.json()
}

export async function createSession(agent_id: string) {
  const res = await fetch(`${API}/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id }),
  })
  if (!res.ok) throw new Error("Failed to create session")
  return res.json()
}
```

- [ ] **Step 3: Create apps/web/lib/ws.ts**

```ts
// lib/ws.ts
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"

type MessageHandler = (data: unknown) => void

export function connectSessionStream(
  sessionId: string,
  onMessage: MessageHandler,
  onClose?: () => void
): () => void {
  const ws = new WebSocket(`${WS_BASE}/v1/sessions/${sessionId}/stream`)

  ws.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data))
    } catch {}
  }

  ws.onclose = () => onClose?.()
  ws.onerror = () => ws.close()

  return () => ws.close()
}
```

- [ ] **Step 4: Add env vars to apps/web/.env.local**

```bash
# apps/web/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/store/ apps/web/lib/ apps/web/.env.local
git commit -m "feat(web): zustand store, api client (SSE), websocket client"
```

---

## Task 8: Sidebar Component

**Files:**
- Create: `apps/web/components/sidebar.tsx`

- [ ] **Step 1: Create apps/web/components/sidebar.tsx**

```tsx
// components/sidebar.tsx
"use client"
import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard, Hammer, Bot, Settings, ChevronDown, ChevronRight, BookOpen, User
} from "lucide-react"

type NavItem = {
  label: string
  href?: string
  children?: { label: string; href: string }[]
}

const NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard" },
  {
    label: "Build",
    children: [
      { label: "Workbench", href: "/build/workbench" },
      { label: "Files", href: "/build/files" },
      { label: "Skills", href: "/build/skills" },
      { label: "Batches", href: "/build/batches" },
    ],
  },
  {
    label: "Managed Agents",
    children: [
      { label: "Quickstart", href: "/quickstart" },
      { label: "Agents", href: "/agents" },
      { label: "Sessions", href: "/sessions" },
      { label: "Environments", href: "/environments" },
      { label: "Credential vaults", href: "/credential-vaults" },
      { label: "Memory stores", href: "/memory-stores" },
    ],
  },
  {
    label: "Setting",
    children: [
      { label: "API keys", href: "/setting/api-keys" },
      { label: "Limits", href: "/setting/limits" },
      { label: "Service accounts", href: "/setting/service-accounts" },
      { label: "Security", href: "/setting/security" },
      { label: "Webhooks", href: "/setting/webhooks" },
    ],
  },
]

const ICONS: Record<string, React.ReactNode> = {
  Dashboard: <LayoutDashboard size={14} />,
  Build: <Hammer size={14} />,
  "Managed Agents": <Bot size={14} />,
  Setting: <Settings size={14} />,
}

function NavSection({ item }: { item: NavItem }) {
  const pathname = usePathname()
  const isActive = item.children?.some((c) => pathname.startsWith(c.href))
  const [open, setOpen] = useState(isActive ?? false)

  if (!item.children) {
    return (
      <Link
        href={item.href!}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded text-[11px] transition-colors",
          pathname === item.href
            ? "text-white bg-white/5"
            : "text-neutral-400 hover:text-white hover:bg-white/5"
        )}
      >
        {ICONS[item.label]}
        {item.label}
      </Link>
    )
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] transition-colors",
          isActive ? "text-white" : "text-neutral-400 hover:text-white hover:bg-white/5"
        )}
      >
        {ICONS[item.label]}
        <span className="flex-1 text-left">{item.label}</span>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <div className="ml-5 mt-0.5 flex flex-col gap-0.5">
          {item.children.map((child) => (
            <Link
              key={child.href}
              href={child.href}
              className={cn(
                "block px-3 py-1 rounded text-[10.5px] transition-colors",
                pathname === child.href
                  ? "text-violet-400 bg-violet-500/10 font-medium"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
              )}
            >
              {child.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="w-[138px] flex-shrink-0 bg-[#111113] border-r border-white/[0.06] flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.06]">
        <div className="w-4 h-4 rounded bg-gradient-to-br from-indigo-500 to-violet-600 flex-shrink-0" />
        <span className="text-[11px] font-bold text-white leading-tight">Claude Console</span>
      </div>

      {/* Workspace dropdown */}
      <div className="px-2 py-2 border-b border-white/[0.06]">
        <button className="w-full flex items-center justify-between bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5">
          <span className="text-[11px] text-neutral-300">Default</span>
          <ChevronDown size={10} className="text-neutral-500" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2 flex flex-col gap-0.5 px-1">
        {NAV.map((item) => (
          <NavSection key={item.label} item={item} />
        ))}
      </nav>

      {/* Bottom */}
      <div className="border-t border-white/[0.06] py-2 px-1">
        <button className="w-full flex items-center gap-2 px-3 py-1.5 text-[10.5px] text-neutral-500 hover:text-neutral-300 rounded hover:bg-white/5 transition-colors">
          <BookOpen size={12} />
          Documentation
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-1.5 text-[10.5px] text-neutral-500 rounded hover:bg-white/5 transition-colors justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center">
              <User size={10} className="text-neutral-400" />
            </div>
            <div className="text-left">
              <div className="text-[10px] text-neutral-300 font-medium">razor</div>
              <div className="text-[9px] text-neutral-600">Admin · org</div>
            </div>
          </div>
          <ChevronDown size={9} className="text-neutral-600" />
        </button>
      </div>
    </aside>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/sidebar.tsx
git commit -m "feat(web): sidebar component with collapsible nav sections"
```

---

## Task 9: Step Bar + Console Layout

**Files:**
- Create: `apps/web/components/step-bar.tsx`
- Create: `apps/web/app/(console)/layout.tsx`

- [ ] **Step 1: Create apps/web/components/step-bar.tsx**

```tsx
// components/step-bar.tsx
"use client"
import { cn } from "@/lib/utils"
import { useAgentStore } from "@/store/agent"

const STEPS = [
  { n: 1, label: "Create agent", sub: "POST /v1/agents" },
  { n: 2, label: "Configure environment", sub: null },
  { n: 3, label: "Start session", sub: null },
  { n: 4, label: "Integrate", sub: null },
]

export function StepBar() {
  const currentStep = useAgentStore((s) => s.currentStep)

  return (
    <div className="h-9 border-b border-white/[0.06] flex items-center px-4 gap-0 bg-[#0e0e10] overflow-x-auto shrink-0">
      <span className="text-[11px] text-neutral-500 pr-4 border-r border-white/[0.06] mr-4 shrink-0">
        Quickstart
      </span>
      {STEPS.map((step, i) => (
        <div key={step.n} className="flex items-center shrink-0">
          <div className="flex items-center gap-1.5 pr-4 border-r border-white/[0.06] mr-4 last:border-0">
            <div
              className={cn(
                "w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0",
                step.n <= currentStep
                  ? "bg-indigo-600 text-white"
                  : "border border-white/10 text-neutral-600"
              )}
            >
              {step.n}
            </div>
            <span
              className={cn(
                "text-[11px]",
                step.n === currentStep
                  ? "text-violet-300 font-semibold"
                  : step.n < currentStep
                  ? "text-neutral-400"
                  : "text-neutral-600"
              )}
            >
              {step.label}
            </span>
            {step.sub && step.n <= currentStep && (
              <span className="bg-white/[0.06] text-neutral-500 text-[9px] font-mono px-1.5 py-0.5 rounded">
                {step.sub}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create apps/web/app/(console)/layout.tsx**

```tsx
// app/(console)/layout.tsx
import { Sidebar } from "@/components/sidebar"
import { StepBar } from "@/components/step-bar"

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-[#0e0e10] text-neutral-200 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <StepBar />
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add root redirect to quickstart**

```tsx
// app/page.tsx
import { redirect } from "next/navigation"
export default function Home() {
  redirect("/quickstart")
}
```

- [ ] **Step 4: Verify layout in browser**

```bash
npm run dev
# Open http://localhost:3000
# Expected: sidebar on left, step-bar at top, no errors
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/step-bar.tsx apps/web/app/
git commit -m "feat(web): step-bar, console layout, root redirect to quickstart"
```

---

## Task 10: Template Browser + Quickstart Panel

**Files:**
- Create: `apps/web/components/template-browser.tsx`
- Create: `apps/web/components/quickstart-panel.tsx`

- [ ] **Step 1: Create apps/web/components/template-browser.tsx**

```tsx
// components/template-browser.tsx
"use client"
import { useState } from "react"
import { Search } from "lucide-react"
import { useAgentStore } from "@/store/agent"

const TEMPLATES = [
  { id: "blank", name: "Blank agent config", desc: "A blank starting point with the core toolset.", yaml: "name: my-agent\ndescription: My custom agent\nmodel: llama3.2\nschedule: null\ntools:\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "researcher", name: "Deep researcher", desc: "Conducts multi-step web research with source synthesis and citations.", yaml: "name: deep-researcher\ndescription: Conducts multi-step web research\nmodel: llama3.2\nschedule: null\ntools:\n  - web_search\n  - memory_store\n  - file_write\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 600" },
  { id: "support", name: "Support agent", desc: "Answers customer questions from your docs and knowledge base.", yaml: "name: support-agent\ndescription: Answers customer questions from docs\nmodel: llama3.2\nschedule: null\ntools:\n  - memory_store\n  - api_call\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "incident", name: "Incident commander", desc: "Triages a Sentry alert, opens a Linear incident ticket.", yaml: "name: incident-commander\ndescription: Triages alerts and opens Linear tickets\nmodel: llama3.2\nschedule: null\ntools:\n  - api_call\n  - slack_send\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "contract", name: "Contract tracker", desc: "Extracts clauses, sets deadline reminders, tracks obligations.", yaml: "name: contract-tracker\ndescription: Extracts clauses and tracks obligations\nmodel: llama3.2\nschedule: null\ntools:\n  - file_read\n  - memory_store\n  - email_send\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "analyst", name: "Data analyst", desc: "Load, explore, and visualize data; build reports from datasets.", yaml: "name: data-analyst\ndescription: Load and visualize data\nmodel: llama3.2\nschedule: null\ntools:\n  - file_read\n  - code_exec\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 600" },
]

export function TemplateBrowser({ onSelect }: { onSelect: (yaml: string, name: string) => void }) {
  const [search, setSearch] = useState("")

  const filtered = TEMPLATES.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.desc.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-white/[0.06] shrink-0">
        <p className="text-[13px] font-semibold text-white mb-2">Browse templates</p>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded px-2.5 py-1.5">
          <Search size={12} className="text-neutral-500 shrink-0" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates"
            className="bg-transparent text-[11px] text-neutral-300 placeholder:text-neutral-600 outline-none flex-1"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 gap-1.5 content-start">
        {filtered.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.yaml, t.name)}
            className="text-left bg-white/[0.03] border border-white/[0.06] rounded-md p-2.5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-colors group"
          >
            <p className="text-[10.5px] font-semibold text-neutral-200 mb-1 group-hover:text-white">
              {t.name}
            </p>
            <p className="text-[10px] text-neutral-600 leading-relaxed">{t.desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create apps/web/components/quickstart-panel.tsx**

```tsx
// components/quickstart-panel.tsx
"use client"
import { useRef } from "react"
import { ArrowUp } from "lucide-react"
import { useAgentStore } from "@/store/agent"
import { cn } from "@/lib/utils"

export function QuickstartPanel({ onSubmit }: { onSubmit: (prompt: string) => void }) {
  const { prompt, setPrompt, isCompiling } = useAgentStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (prompt.trim() && !isCompiling) onSubmit(prompt.trim())
    }
  }

  return (
    <div className="flex flex-col h-full border-r border-white/[0.06]">
      {/* Center content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <h2 className="text-[15px] font-semibold text-white mb-2">
          What do you want to build?
        </h2>
        <p className="text-[11px] text-neutral-500">
          Describe your agent or start with a template.
        </p>
      </div>

      {/* Bottom textarea */}
      <div className="p-3 border-t border-white/[0.06] shrink-0">
        <div className="flex items-end gap-2 bg-[#1a1a1e] border border-white/[0.08] rounded-lg px-3 py-2.5">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your agent..."
            rows={1}
            className="flex-1 bg-transparent text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none resize-none max-h-32 leading-relaxed"
            style={{ minHeight: "20px" }}
          />
          <button
            onClick={() => prompt.trim() && !isCompiling && onSubmit(prompt.trim())}
            disabled={!prompt.trim() || isCompiling}
            className={cn(
              "w-6 h-6 rounded flex items-center justify-center shrink-0 transition-colors",
              prompt.trim() && !isCompiling
                ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                : "bg-white/[0.06] text-neutral-600 cursor-not-allowed"
            )}
          >
            <ArrowUp size={13} />
          </button>
        </div>
        {isCompiling && (
          <p className="text-[10px] text-indigo-400 mt-1.5 text-center">
            Compiling agent spec...
          </p>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/template-browser.tsx apps/web/components/quickstart-panel.tsx
git commit -m "feat(web): template browser, quickstart prompt panel"
```

---

## Task 11: YAML Editor + Stream Viewer

**Files:**
- Create: `apps/web/components/yaml-editor.tsx`
- Create: `apps/web/components/stream-viewer.tsx`

- [ ] **Step 1: Create apps/web/components/yaml-editor.tsx**

```tsx
// components/yaml-editor.tsx
"use client"
import dynamic from "next/dynamic"
import { useAgentStore } from "@/store/agent"
import { cn } from "@/lib/utils"
import yaml from "yaml"

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false })

export function YamlEditor({
  onCreateAgent,
}: {
  onCreateAgent: (name: string, yamlStr: string) => void
}) {
  const { yaml: yamlStr, setYaml, activeTab, setActiveTab, agentId, agentName, setAgentName } =
    useAgentStore()

  const jsonValue = (() => {
    try {
      return JSON.stringify(yaml.parse(yamlStr), null, 2)
    } catch {
      return "{}"
    }
  })()

  const displayValue = activeTab === "yaml" ? yamlStr : jsonValue
  const language = activeTab === "yaml" ? "yaml" : "json"

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-white/[0.06] shrink-0">
        {(["yaml", "json"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "text-[11px] font-medium pb-1 transition-colors uppercase tracking-wide",
              activeTab === tab
                ? "text-violet-400 border-b border-violet-400"
                : "text-neutral-500 hover:text-neutral-300"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-hidden">
        {yamlStr ? (
          <MonacoEditor
            value={displayValue}
            language={language}
            theme="vs-dark"
            onChange={(v) => {
              if (activeTab === "yaml") setYaml(v ?? "")
            }}
            options={{
              fontSize: 12,
              lineHeight: 1.7,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: "on",
              readOnly: activeTab === "json",
              padding: { top: 12, bottom: 12 },
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-neutral-600 text-[12px]">
            Type a prompt or select a template to generate your agent spec.
          </div>
        )}
      </div>

      {/* Bottom actions */}
      {yamlStr && !agentId && (
        <div className="border-t border-white/[0.06] px-4 py-2.5 flex items-center gap-3 shrink-0">
          <input
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Agent name..."
            className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded px-2.5 py-1.5 text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none"
          />
          <button
            onClick={() => onCreateAgent(agentName || "my-agent", yamlStr)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium px-3 py-1.5 rounded transition-colors shrink-0"
          >
            Create agent
          </button>
        </div>
      )}

      {agentId && (
        <div className="border-t border-white/[0.06] px-4 py-2 shrink-0">
          <p className="text-[10px] text-emerald-500">
            ✓ Agent created — proceed to Configure environment
          </p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create apps/web/components/stream-viewer.tsx**

```tsx
// components/stream-viewer.tsx
"use client"
import { useAgentStore, StreamEvent } from "@/store/agent"
import { cn } from "@/lib/utils"

function EventRow({ event }: { event: StreamEvent }) {
  if (event.type === "token") {
    return <span className="text-neutral-300 text-[11px]">{event.content}</span>
  }
  if (event.type === "tool_call") {
    return (
      <div className="flex items-start gap-2 py-1">
        <span className="text-violet-400 text-[10px] font-mono shrink-0">→ {event.tool}</span>
        <span className="text-neutral-500 text-[10px] font-mono truncate">{event.input}</span>
      </div>
    )
  }
  if (event.type === "tool_result") {
    return (
      <div className="flex items-start gap-2 py-1">
        <span className="text-emerald-400 text-[10px] font-mono shrink-0">← {event.tool}</span>
        <span className="text-neutral-400 text-[10px] truncate">{event.output}</span>
      </div>
    )
  }
  if (event.type === "status") {
    const color =
      event.status === "completed"
        ? "text-emerald-400"
        : event.status === "failed"
        ? "text-red-400"
        : "text-yellow-400"
    return (
      <div className={cn("text-[10px] font-semibold uppercase tracking-wider py-1", color)}>
        ● {event.status}
      </div>
    )
  }
  if (event.type === "checkpoint") {
    return (
      <div className="text-[10px] text-neutral-600 py-0.5">
        checkpoint {event.step}: {event.state}
      </div>
    )
  }
  return null
}

export function StreamViewer() {
  const { streamEvents, sessionStatus } = useAgentStore()

  if (streamEvents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-neutral-600 text-[11px]">
        Session stream will appear here when you start a session.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-white/[0.06] flex items-center gap-2 shrink-0">
        <span className="text-[11px] font-semibold text-white">Execution stream</span>
        <span
          className={cn(
            "text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded",
            sessionStatus === "running"
              ? "bg-yellow-500/10 text-yellow-400"
              : sessionStatus === "completed"
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400"
          )}
        >
          {sessionStatus}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 font-mono leading-relaxed">
        {streamEvents.map((e, i) => (
          <EventRow key={i} event={e} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/yaml-editor.tsx apps/web/components/stream-viewer.tsx
git commit -m "feat(web): yaml/json monaco editor, realtime stream viewer"
```

---

## Task 12: Quickstart Page (Wire Everything)

**Files:**
- Create: `apps/web/app/(console)/quickstart/page.tsx`

- [ ] **Step 1: Create apps/web/app/(console)/quickstart/page.tsx**

```tsx
// app/(console)/quickstart/page.tsx
"use client"
import { useCallback } from "react"
import { useAgentStore } from "@/store/agent"
import { compileAgent, createAgent, createSession } from "@/lib/api"
import { connectSessionStream } from "@/lib/ws"
import { QuickstartPanel } from "@/components/quickstart-panel"
import { TemplateBrowser } from "@/components/template-browser"
import { YamlEditor } from "@/components/yaml-editor"
import { StreamViewer } from "@/components/stream-viewer"

export default function QuickstartPage() {
  const {
    yaml, agentId, sessionId,
    setYaml, setIsCompiling, setAgentId, setSessionId,
    addStreamEvent, clearStreamEvents, setSessionStatus,
    setCurrentStep,
  } = useAgentStore()

  const handleCompile = useCallback(async (prompt: string) => {
    setIsCompiling(true)
    setYaml("")
    try {
      await compileAgent(prompt, (token) => {
        useAgentStore.setState((s) => ({ yaml: s.yaml + token }))
      })
    } catch (e) {
      console.error("Compile error", e)
    } finally {
      setIsCompiling(false)
    }
  }, [setIsCompiling, setYaml])

  const handleTemplateSelect = useCallback((yaml: string, name: string) => {
    useAgentStore.setState({ yaml, agentName: name })
  }, [])

  const handleCreateAgent = useCallback(async (name: string, yamlStr: string) => {
    try {
      const agent = await createAgent(name, yamlStr)
      setAgentId(agent.id)
    } catch (e) {
      console.error("Create agent error", e)
    }
  }, [setAgentId])

  const handleStartSession = useCallback(async () => {
    if (!agentId) return
    clearStreamEvents()
    setSessionStatus("running")
    try {
      const session = await createSession(agentId)
      setSessionId(session.id)
      setCurrentStep(3)
      const disconnect = connectSessionStream(
        session.id,
        (data) => {
          const event = data as Parameters<typeof addStreamEvent>[0]
          addStreamEvent(event)
          if (event.type === "status") {
            if (event.status === "completed" || event.status === "failed") {
              setSessionStatus(event.status)
              disconnect()
            }
          }
        },
        () => setSessionStatus("completed")
      )
    } catch (e) {
      console.error("Session error", e)
      setSessionStatus("failed")
    }
  }, [agentId, clearStreamEvents, setSessionStatus, setSessionId, setCurrentStep, addStreamEvent])

  const showStream = sessionId !== null

  return (
    <div className="flex h-full">
      {/* Left: prompt input */}
      <div className="w-[42%] shrink-0">
        <QuickstartPanel onSubmit={handleCompile} />
      </div>

      {/* Right: template browser → yaml editor → stream */}
      <div className="flex-1 flex flex-col min-w-0">
        {showStream ? (
          <StreamViewer />
        ) : yaml ? (
          <YamlEditor onCreateAgent={handleCreateAgent} />
        ) : (
          <TemplateBrowser onSelect={handleTemplateSelect} />
        )}

        {/* Start session button — appears after agent is created */}
        {agentId && !sessionId && (
          <div className="border-t border-white/[0.06] px-4 py-2.5 flex justify-end shrink-0">
            <button
              onClick={handleStartSession}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold px-4 py-1.5 rounded transition-colors"
            >
              Start session →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Test full flow in browser**

```
1. Open http://localhost:3000 (redirects to /quickstart)
2. Type: "buat agent yang research AI startup setiap pagi"
3. Press Enter — YAML should stream into editor
4. Click "Create agent" — agent saved to DB
5. Click "Start session →" — stream events appear in StreamViewer
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/\(console\)/quickstart/
git commit -m "feat(web): quickstart page, full flow compile→create→stream"
```

---

## Task 13: Agent List Page + Sessions Page

**Files:**
- Create: `apps/web/app/(console)/agents/page.tsx`
- Create: `apps/web/app/(console)/sessions/page.tsx`

- [ ] **Step 1: Create apps/web/app/(console)/agents/page.tsx**

```tsx
// app/(console)/agents/page.tsx
"use client"
import { useEffect, useState } from "react"
import { listAgents } from "@/lib/api"
import { formatDistanceToNow } from "date-fns"

interface Agent {
  id: string
  name: string
  status: string
  created_at: string
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-[15px] font-semibold text-white mb-4">Agents</h1>
      {loading ? (
        <p className="text-[11px] text-neutral-600">Loading...</p>
      ) : agents.length === 0 ? (
        <p className="text-[11px] text-neutral-600">
          No agents yet. Go to{" "}
          <a href="/quickstart" className="text-violet-400 underline">
            Quickstart
          </a>{" "}
          to create one.
        </p>
      ) : (
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.06] text-left text-neutral-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                <td className="py-2 text-neutral-200 font-mono">{a.name}</td>
                <td className="py-2">
                  <span className="bg-emerald-500/10 text-emerald-400 text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase">
                    {a.status}
                  </span>
                </td>
                <td className="py-2 text-neutral-500">
                  {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

Install date-fns: `npm install date-fns`

- [ ] **Step 2: Create apps/web/app/(console)/sessions/page.tsx**

```tsx
// app/(console)/sessions/page.tsx
export default function SessionsPage() {
  return (
    <div className="p-6">
      <h1 className="text-[15px] font-semibold text-white mb-2">Sessions</h1>
      <p className="text-[11px] text-neutral-600">
        Session history will appear here after running agents from Quickstart.
      </p>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/\(console\)/agents/ apps/web/app/\(console\)/sessions/
git commit -m "feat(web): agents list page, sessions stub page"
```

---

## Task 14: Final Polish + Integration Verify

- [ ] **Step 1: Add NEXT_PUBLIC env to apps/web/.env.local**

Verify `.env.local` has both:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

- [ ] **Step 2: Verify full end-to-end flow**

```
1. docker compose up -d            → Postgres + Redis running
2. cd apps/api && uvicorn main:app --reload --port 8000
3. cd apps/web && npm run dev
4. Open http://localhost:3000
5. Type prompt → YAML compiles → Create agent → Start session → Stream events
6. Navigate to /agents → agent appears in list
```

- [ ] **Step 3: Add .gitignore entries**

Add to root `.gitignore`:
```
apps/web/.next/
apps/web/node_modules/
apps/api/__pycache__/
apps/api/.env
.env
.superpowers/
```

- [ ] **Step 4: Commit and push**

```bash
git add .gitignore
git commit -m "chore: gitignore, env files"
git push origin main
```

---

## Out of Scope (future iterations)

- Temporal workflow orchestration
- Qdrant vector memory (memory_store tool is stubbed)
- Kubernetes / production deployment
- Scheduler / cron execution (schedule field stored, not executed)
- Multi-agent supervisor/worker
- Authentication / billing
- Step 2 (Configure environment) and Step 4 (Integrate) UI pages
