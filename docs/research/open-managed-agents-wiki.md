# Wiki: open-managed-agents

**Repo:** https://github.com/rogeriochaves/open-managed-agents  
**Author:** Rogerio Chaves  
**License:** AGPL-3.0  
**Stack:** TypeScript, Hono, React, Vercel AI SDK, SQLite/PostgreSQL  
**Posisi:** Self-hosted open-source alternative to Anthropic's Claude Managed Agents

---

## Ringkasan

Open Managed Agents (OMA) adalah platform manajemen AI agent yang dapat di-self-host, dengan fitur enterprise governance (org/team/RBAC), multi-LLM support, dan credential vault terenkripsi. Dirancang untuk perusahaan yang tidak bisa mengirim data ke platform agent pihak ketiga.

---

## Arsitektur

```
packages/
├── server/         # Hono API server (TypeScript)
│   └── src/
│       ├── engine/ # Core agent execution loop
│       ├── db/     # SQLite/PostgreSQL dual-backend
│       ├── routes/ # REST API endpoints
│       ├── providers/ # LLM provider integrations
│       └── middleware/
├── web/            # React + Vite frontend
├── types/          # Shared TypeScript types
├── cli/            # CLI client
└── scenario-tests/ # BDD end-to-end tests (Gherkin)

specs/              # 40+ feature files (BDD specs)
helm/               # Kubernetes Helm chart
```

### Database Layer

Dual-backend unik: satu schema berjalan di SQLite dan PostgreSQL.
- Placeholder translation otomatis: `?` (SQLite) ↔ `$1...$N` (PostgreSQL)
- Auto-migration on boot
- Encrypted credential storage via AES-256-GCM

### LLM Provider Abstraction

7 provider via Vercel AI SDK:
| Provider | Type |
|---|---|
| Anthropic (Claude) | Cloud |
| OpenAI | Cloud |
| Google Gemini | Cloud |
| Mistral | Cloud |
| Groq | Cloud |
| Ollama | Self-hosted (localhost:11434) |
| OpenAI-compatible API | Self-hosted/Custom |

Per-agent provider selection memungkinkan deployment heterogen.

---

## Agent Model

### Struktur Agent

```typescript
Agent {
  id, name, description,
  model: { id, speed: "standard" | "fast" },
  tools: AgentToolset,           // built-in tools
  mcp_servers: MCPToolset[],     // MCP protocol tools
  custom_tools: CustomTool[],    // user-defined tools
  skills: (AnthropicSkill | CustomSkill)[]
}
```

### Built-in Tools (AgentToolset20260401)

| Tool | Fungsi |
|---|---|
| `bash` | Execute shell commands |
| `edit` | Edit files |
| `read` | Read files |
| `write` | Write files |
| `glob` | File pattern matching |
| `grep` | Search in files |
| `web_fetch` | HTTP fetch |
| `web_search` | Web search |

### Tool Permission Policies

Setiap tool bisa dikonfigurasi dengan permission policy: `allowed`, `blocked`, atau `requires-approval`.

### Custom Tools

User-defined tools dengan JSON schema input. Eksekusinya di-pause—session masuk status `idle` dan menunggu user/eksternal menyediakan tool result. Ini seperti human-in-the-loop pattern.

### MCP Tools

Tools dari MCP server di-prefix: `__mcp__<connector>__<tool>`. Jika connector tidak tersedia, tool dilewati tanpa crash (**graceful degradation**).

---

## Engine: Agent Execution Loop

Ini bagian paling menarik secara teknis.

### Flow

```
1. Resolve tools (builtin + MCP + custom)
2. Build messages from event history (event sourcing)
3. CHECK session status in DB → if "terminated", bail out
4. Call LLM via provider
5. If stop_reason = "tool_use":
   a. Built-in tools: execute immediately
   b. MCP tools: route to MCP client
   c. Custom tools: session → idle, wait for user
6. Emit SSE events for each action
7. Store events to DB
8. Loop back to step 3
```

### Cooperative Cancellation

Sebelum setiap LLM call, engine cek status session di DB:
```sql
SELECT status FROM sessions WHERE id = ?
```
Jika status `"terminated"` → stop. Sederhana tapi efektif — tidak ada mid-turn interruption.

### Event Sourcing

Semua actions disimpan sebagai timestamped events di DB:
- LLM messages, tool calls, tool results
- `buildMessagesFromEvents()` merekonstruksi conversation history dari events
- Session state selalu bisa di-replay

### Streaming via SSE

`createSSEEmitter()` menggunakan `ReadableStream` yang mengalirkan newline-delimited JSON (`data: {event}\n\n`) dan menutup dengan sentinel `[DONE]`.

### Error Handling

Tiga level:
1. **Tool level**: Failed call → `is_error: true` → LLM menerima error sebagai context
2. **Connector level**: MCP server tidak tersedia → di-skip, agent tetap jalan
3. **Loop level**: Uncaught exception → emit `session.error` → status `terminated`

---

## Session Model

```typescript
Session {
  status: "rescheduling" | "running" | "idle" | "terminated",
  resources: [
    FileResource,               // file mounting
    GitHubRepositoryResource,   // repo checkout dengan branch/commit
  ],
  usage: { tokens, cache_metrics },
  vault_ids: string[]           // linked credential vaults
}
```

**Session Resources** yang menarik: agent bisa di-attach ke GitHub repository, termasuk checkout branch/commit tertentu. Agent punya akses ke codebase.

---

## Enterprise Governance

### Hierarki Akses

```
Organization
└── Team
    └── Project
        └── Agent / Session
```

### Roles

| Role | Akses |
|---|---|
| Admin | Full resource + policy management |
| Member | Create dan execute agent dalam scope |
| Viewer | Read-only |

### Per-Team Controls

- LLM provider availability
- Rate limits (requests per minute)
- Monthly budget caps
- MCP connector policies: `allowed` / `blocked` / `requires-approval`

### Governance-as-Code

Config governance bisa di-deploy via JSON file → GitOps pattern. Access controls sinkron dengan release.

### Audit Logging

"Every mutation logged with user + resource + details" — comprehensive audit trail untuk compliance.

---

## Credential Vault

- Enkripsi: AES-256-GCM
- Vault bisa di-attach ke session via `vault_ids`
- Tools bisa mengakses credentials tanpa agent "tahu" nilainya
- Mirip dengan per-agent secrets di Clouma, tapi terenkripsi dan bisa di-share antar sessions

---

## Testing

**387 automated tests** across 4 packages:
- Schema alignment linting — mencegah silent no-ops
- Cursor pagination validation
- Date range filtering (`gt|gte|lt|lte`)
- MCP engine integration dengan real tool calling
- Governance enforcement tests
- E2E scenario tests dengan live LLM

**BDD Specs** (40+ feature files di `specs/`):
- `engine-cooperative-cancellation.feature`
- `engine-mcp.feature`, `engine-mcp-e2e.feature`
- `vaults-api.feature`
- `governance-api.feature`
- `audit-log-ui.feature`
- `session-detail-tool-tracing.feature`

---

## Deployment

### Docker Compose

```yaml
services:
  postgres:   # postgres:16-alpine
  server:     # port 3001
  web:        # port 5173 → 80
```

### Kubernetes (Helm)

Tiga konfigurasi DB:
1. SQLite dengan PVC (single-node)
2. Embedded PostgreSQL (cluster)
3. External PostgreSQL (RDS, Cloud SQL, Neon, Supabase)

### Self-Hosted Mode

Air-gapped deployment dimungkinkan dengan Ollama — tidak perlu koneksi internet setelah install.

---

## API Design

- 1:1 API mapping: web, CLI, dan programmatic client pakai endpoint yang sama
- OpenAPI docs auto-generate dari Zod schema definitions
- Resource families: agents, sessions, events, providers, vaults, governance

---

## Perbandingan dengan Clouma

| Fitur | OMA | Clouma |
|---|---|---|
| Backend | TypeScript + Hono | Python + FastAPI |
| Agent runtime | Custom engine (Vercel AI SDK) | Google ADK |
| Streaming | SSE | WebSocket + SSE |
| DB | SQLite / PostgreSQL | PostgreSQL |
| Auth | Built-in (SSO support) | ❌ Belum ada |
| Governance (RBAC) | ✅ Org/Team/Project | ❌ Belum ada |
| Credential vault | ✅ AES-256-GCM | ⚠️ Plaintext MVP |
| MCP support | ✅ Production-ready | ❌ Belum |
| Built-in tools | bash, edit, read, write, glob, grep, web | 12 tools custom |
| Custom tools | ✅ User-defined JSON schema | ❌ Admin-only |
| Cron scheduler | ❌ Tidak ada | ✅ Baru diimplementasi |
| Skills/sub-agents | ✅ AnthropicSkill + CustomSkill | ✅ 6 predefined |
| GitHub resource | ✅ Repository checkout | ❌ |
| BDD tests | 387 tests + Gherkin specs | pytest unit tests |
| CLI | ✅ | ❌ |
| Self-host | ✅ Docker + Helm | ✅ Docker |
| Air-gapped | ✅ via Ollama | ✅ via Ollama |

---

## Referensi

- Repo: https://github.com/rogeriochaves/open-managed-agents
- Vercel AI SDK: https://sdk.vercel.ai
- MCP (Model Context Protocol): https://modelcontextprotocol.io
