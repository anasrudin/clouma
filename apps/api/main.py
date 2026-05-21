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

import api.models.agent_secret  # noqa: F401 — registers table with Base for create_tables()
from .routers import agents, sessions, tools, compile as compile_router, dry_run as dry_run_router
from .routers import skills as skills_router
from .routers import secrets as secrets_router
app.include_router(agents.router, prefix="/v1")
app.include_router(sessions.router, prefix="/v1")
app.include_router(tools.router, prefix="/v1")
app.include_router(compile_router.router, prefix="/v1")
app.include_router(dry_run_router.router, prefix="/v1")
app.include_router(skills_router.router, prefix="/v1")
app.include_router(secrets_router.router, prefix="/v1")

@app.get("/health")
async def health():
    return {"status": "ok"}
