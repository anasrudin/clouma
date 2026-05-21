# Design: Tools, Credentials & Agent Awareness

**Date:** 2026-05-21
**Status:** Approved

---

## Overview

Three independent subsystems implemented together as a coherent feature set:

- **A — Content Tools**: 6 new builtin tools (write_file, rss_fetch, youtube_transcript, pdf_extract, pptx_generate, docx_generate)
- **C — Agent Tool Awareness**: Compiler upgrade so generated agents know which tools need credentials and how to use them
- **D — Per-Agent Credential System**: DB-backed secrets per agent, web UI for input, runtime injection into tools

---

## Section A: Content Tools

### New tools in `apps/api/agent_runtime/tools/builtin.py`

| Tool | Signature | Returns | Dep |
|---|---|---|---|
| `write_file` | `path: str, content: str, mode: str = "w"` | `str` (path written) | stdlib |
| `rss_fetch` | `url: str, max_items: int = 10` | `list[dict]` — `{title, url, summary, published}` | `feedparser` |
| `youtube_transcript` | `video_url: str, language: str = "en"` | `str` transcript text | `youtube-transcript-api` |
| `pdf_extract` | `path_or_url: str` | `str` extracted text | `pymupdf` |
| `pptx_generate` | `title: str, slides: list[dict], output_path: str` | `str` path to .pptx | `python-pptx` (installed) |
| `docx_generate` | `sections: list[dict], output_path: str` | `str` path to .docx | `python-docx` |

**`slides` schema for `pptx_generate`:**
```json
[{"title": "Slide title", "bullets": ["point 1", "point 2"]}]
```

**`sections` schema for `docx_generate`:**
```json
[{"heading": "Section title", "body": "Paragraph text"}]
```

**`pdf_extract` behaviour:**
- If `path_or_url` starts with `http`, fetch via httpx then extract
- Otherwise treat as local filesystem path

### New dependencies (requirements.txt)

```
feedparser>=6.0,<7
youtube-transcript-api>=0.6,<1
pymupdf>=1.24,<2
python-docx>=1.1,<2
```

### Error handling

All tools return `"[error] <message>"` strings on failure (consistent with `run_python`). No exceptions propagate to the agent runtime.

---

## Section C: Agent Tool Awareness

### Problem

Currently the compiler system prompt only lists tool names. Agents don't know:
- Which tools require credentials (and what key names)
- How to structure complex inputs (e.g. `slides` for pptx)
- What `permissions` to declare in the YAML

### Changes to `apps/api/agent_runtime/compiler.py`

**`_build_tool_catalog_markdown()` upgrade:** Add `requires` column:

```
| name               | description | params         | requires            |
|--------------------|-------------|----------------|---------------------|
| telegram_send      | ...         | chat_id,text   | telegram:bot_token  |
| confluence_search  | ...         | query          | confluence:api_key,confluence:url |
| youtube_transcript | ...         | video_url      | -                   |
| pptx_generate      | ...         | title,slides,output_path | -        |
```

**System prompt addition:**

```
If a tool lists requirements in the `requires` column, include a `permissions`
block in the YAML:

  permissions:
    - service: telegram
      keys: [bot_token]

Agents will only have access to credentials they declare in `permissions`.
```

**`slides` / `sections` usage hints added to system prompt** so LLM knows the expected structure.

### Changes to `apps/api/agent_runtime/validator.py`

Add a soft warning (not hard error) when a tool with required credentials is used but `permissions` is not declared:

```python
ValidationDelta.missing_permissions: list[str]  # new field
```

Dry-run and compile still succeed with warnings. The warning surfaces in the UI as a yellow banner.

---

## Section D: Per-Agent Credential System

### DB Model — `AgentSecret`

New file: `apps/api/models/agent_secret.py`

```python
class AgentSecret(Base):
    __tablename__ = "agent_secrets"

    id: str (UUID PK)
    agent_id: str (FK → agents.id, CASCADE DELETE)
    service: str      # "telegram" | "confluence" | "slack" | custom
    key_name: str     # "bot_token" | "api_key" | "space_url"
    value: str        # plaintext for MVP; encrypted at rest in Phase 8+
    created_at: datetime
    updated_at: datetime

    __table_args__ = UniqueConstraint("agent_id", "service", "key_name")
```

### Alembic migration

New migration: `add_agent_secrets_table`

### API Endpoints — `apps/api/routers/secrets.py`

```
GET    /v1/agents/{agent_id}/secrets
       → list[{service, key_name, created_at}]   # values never returned

POST   /v1/agents/{agent_id}/secrets
       body: {service, key_name, value}
       → 201 {id, service, key_name, created_at}
       upsert on (agent_id, service, key_name)

DELETE /v1/agents/{agent_id}/secrets/{service}/{key_name}
       → 204
```

### Runtime Injection — `apps/api/agent_runtime/credentials.py`

New module exposing one function:

```python
async def get_agent_secret(
    db: AsyncSession,
    agent_id: str,
    service: str,
    key_name: str,
) -> str | None:
    """Look up a credential for the given agent. Returns None if not set."""
```

Tools that need credentials call this lazily:

```python
# In telegram_send tool (future):
from agent_runtime.credentials import get_agent_secret_sync
token = get_agent_secret_sync(agent_id, "telegram", "bot_token")
```

`get_agent_secret_sync` wraps the async version using a dedicated sync DB session.

### Credential-aware tools

These tools (implemented in this sprint or future) read their credentials via `get_agent_secret_sync`:

| Tool | Service | Keys |
|---|---|---|
| `telegram_send` | `telegram` | `bot_token`, `chat_id` |
| `confluence_search` | `confluence` | `api_key`, `base_url` |
| `confluence_create_page` | `confluence` | `api_key`, `base_url`, `space_key` |
| `slack_send` | `slack` | `webhook_url` |

### Web UI — Integrations panel

New component: `apps/web/components/agent-integrations.tsx`

Shown in the agent create/edit form below the tool catalog, above the YAML editor.

**Layout:**
```
Integrations
[+ Add credential]

Service      Key name       Value          Action
──────────── ────────────── ────────────── ──────
Telegram     bot_token      ••••••••       [Delete]
Confluence   api_key        ••••••••       [Delete]
```

- Values display as `••••••••` after save (never shown again)
- "Add credential" opens an inline form: dropdown (Telegram/Confluence/Slack/Custom) + key_name input + value input
- On save: `POST /v1/agents/{id}/secrets`
- On delete: `DELETE /v1/agents/{id}/secrets/{service}/{key_name}`
- Shown only for existing agents (not during initial creation)

---

## Implementation Order

1. **Content tools + deps** — `builtin.py`, `requirements.txt`
2. **AgentSecret model + migration** — `models/agent_secret.py`, alembic
3. **Secrets API** — `routers/secrets.py`, register in `main.py`
4. **Credentials runtime module** — `agent_runtime/credentials.py`
5. **Compiler upgrade** — tool catalog with `requires` column + permissions hints
6. **Validator upgrade** — `missing_permissions` soft warning
7. **Web UI: Integrations panel** — `components/agent-integrations.tsx`
8. **Tests** — unit tests for each layer

---

## Dependencies summary

```
# requirements.txt additions
feedparser>=6.0,<7
youtube-transcript-api>=0.6,<1
pymupdf>=1.24,<2
python-docx>=1.1,<2
```

No new frontend packages needed (uses existing shadcn/ui components).

---

## Out of scope

- Encryption at rest for credential values (Phase 8+)
- Per-user credentials (requires auth system)
- `telegram_send`, `confluence_*`, `slack_send` tool implementations (tracked separately — credential infrastructure is the blocker)
- Anthropic MCP tool integration
