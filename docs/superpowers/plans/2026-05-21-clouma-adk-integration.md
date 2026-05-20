# Clouma + ADK 2 Integration Plan

> **Tujuan:** Ganti komponen "compile prompt → YAML" + executor custom di MVP plan
> dengan integrasi ADK 2 sebagai runtime, dan tukar pipeline LLM-YAML rawan halusinasi
> dengan **catalog-driven structured generation**.
>
> **Sumber rujukan utama:**
> - [docs/adk/2.0.md](../../adk/2.0.md) — ADK 2 overview & breaking changes
> - [docs/adk/agents/config.md](../../adk/agents/config.md) — `AgentConfig` YAML/JSON
> - [docs/adk/tools.md](../../adk/tools.md) — Tool API
> - [docs/adk/runtime.md](../../adk/runtime.md) — `Runner`, eksekusi, Event stream
> - [docs/adk/sessions.md](../../adk/sessions.md) — `BaseSessionService`
> - [docs/superpowers/plans/2026-05-20-clouma-console-mvp.md](2026-05-20-clouma-console-mvp.md) — plan MVP yang sedang direvisi
>
> **Prasyarat:** Task 1–4 di MVP plan (scaffold, FastAPI core, Postgres, Next.js shell)
> sudah ada atau sedang dikerjakan. Plan ini menggantikan Task 5–7 dari MVP plan.

---

## Keputusan desain

| Pertanyaan | Keputusan | Alasan |
|---|---|---|
| Skema agent | Pakai ADK `AgentConfig` JSON schema langsung | Sudah ada, terstandar, langsung loadable ke `Runner` |
| Compile prompt → spec | LLM dengan `response_format=json_schema` constrained ke `AgentConfig` | Tidak halusinasi, tidak parse YAML, validasi otomatis |
| Tool discovery | Tool registry server-side dengan introspeksi type hints | LLM dapat catalog real-time; user bisa lihat di UI |
| Eksekusi agent | ADK `Runner` + `LlmAgent` (atau workflow agent) | Tidak bangun executor sendiri |
| Session storage | Custom `BaseSessionService` simpan event sebagai JSON blob di Postgres | Per dok 2.0: blob storage = zero schema migration |
| Stream ke WS | Forward ADK `Event` stream langsung ke WebSocket frontend | Native streaming, no custom protocol |
| YAML editor | Tetap ada tapi sebagai "Advanced view"; default = Form view | User awam tidak perlu menyentuh YAML |
| ADK version | `google-adk~=2.0` | GA, graph workflow ready untuk fitur multi-agent fase berikutnya |

---

## Phase 1 — Tool Registry

**Goal:** Daftar tools server-side dengan JSON schema otomatis dari type hints.

- [ ] **1.1** Tambah `google-adk~=2.0` ke `apps/api/requirements.txt`
- [ ] **1.2** Buat `apps/api/agent_runtime/tools/__init__.py` dengan `TOOL_REGISTRY: dict[str, ToolEntry]`
- [ ] **1.3** Buat decorator `@register_tool(name, description)` yang:
  - introspeksi signature & type hints → JSON schema (pakai `pydantic.TypeAdapter`)
  - wrap fungsi sebagai ADK `FunctionTool`
  - daftar ke `TOOL_REGISTRY`
- [ ] **1.4** Tulis 4 starter tool di `apps/api/agent_runtime/tools/builtin.py`:
  - `web_search(query: str, max_results: int = 5) -> list[dict]`
  - `http_get(url: str) -> str`
  - `read_file(path: str) -> str`
  - `current_time(tz: str = "UTC") -> str`
- [ ] **1.5** Endpoint `GET /tools` → return `[{name, description, input_schema}]` untuk UI catalog
- [ ] **1.6** Unit test: import builtin tools, assert registry punya 4 entry, schema valid JSON Schema

---

## Phase 2 — Catalog-driven Compiler

**Goal:** Ganti `services/compiler.py` (MVP plan Task 5) dengan structured-output yang tidak bisa halusinasi.

- [ ] **2.1** Download ADK `AgentConfig` JSON schema ke `apps/api/agent_runtime/schemas/agent_config.json`
  - sumber: `https://raw.githubusercontent.com/google/adk-python/refs/heads/main/src/google/adk/agents/config_schemas/AgentConfig.json`
- [ ] **2.2** Buat `apps/api/agent_runtime/compiler.py`:
  - input: user prompt (string)
  - kumpulkan tool catalog dari registry → ringkasan markdown table untuk system prompt
  - panggil LLM dengan:
    - `response_format={"type":"json_schema","json_schema":{"name":"agent_config","schema":AGENT_CONFIG_SCHEMA,"strict":True}}`
    - system: "Pilih tools HANYA dari katalog. Output AgentConfig JSON."
  - return: validated `dict`
- [ ] **2.3** Post-validation:
  - assert `cfg["tools"] ⊆ TOOL_REGISTRY.keys()` → raise 422 dengan daftar tool yang unknown
  - assert `cfg["model"]` ada di allowlist (sementara: `["gemini-flash-latest","gpt-4o-mini"]`)
- [ ] **2.4** SSE endpoint `POST /agents/compile` stream:
  - event `status` "discovering tools" / "calling llm" / "validating"
  - event `result` dengan agent config JSON final
  - event `error` jika validation gagal (sertakan delta untuk dibetulkan)
- [ ] **2.5** Test: prompt "ringkas email saya" → assert tool `read_file` tidak dipilih kalau bukan email; assert tool `web_search` boleh ada; assert schema valid.

---

## Phase 3 — Persist as ADK-Compatible Config

**Goal:** Simpan agent dalam bentuk yang bisa di-`from_config()` ADK tanpa transformasi.

- [ ] **3.1** Update model `apps/api/models/agent.py`:
  - kolom `config_json: dict` (canonical, validated against AgentConfig)
  - kolom `yaml_cache: str | null` (rendered on save untuk export, regenerable)
  - drop kolom DSL custom dari MVP plan (kalau sudah ada)
- [ ] **3.2** `POST /agents` body = AgentConfig JSON, simpan setelah validasi
- [ ] **3.3** `GET /agents/{id}?format=yaml` → render `yaml.safe_dump(config_json)` dengan header `# yaml-language-server: $schema=...AgentConfig.json`
- [ ] **3.4** Migration: tabel `agents` minimal `id`, `created_at`, `name`, `description`, `config_json`, `yaml_cache`

---

## Phase 4 — Runtime via ADK Runner

**Goal:** Ganti executor custom (MVP plan Task 6) dengan ADK `Runner`.

- [ ] **4.1** Buat `apps/api/agent_runtime/session_service.py`:
  - subclass `BaseSessionService`
  - simpan `Event` sebagai JSON blob di tabel `session_events` (kolom `event_json: jsonb`)
  - **PENTING per dok 2.0:** jangan map field ke kolom rigid — pakai blob → kompatibel dengan field `node_info`/`output` baru di ADK 2
- [ ] **4.2** Buat `apps/api/agent_runtime/runner_factory.py`:
  - input: `agent_id` → load `config_json` dari DB → `config_agent_utils.from_config_dict(cfg, tool_registry=TOOL_REGISTRY)`
  - wrap di `Runner(agent=..., session_service=PostgresSessionService(...))`
- [ ] **4.3** WebSocket endpoint `/sessions/{session_id}/ws`:
  - client kirim `{"input": "..."}` → backend panggil `runner.run_async(user_id, session_id, new_message)`
  - **JANGAN** append event manual ke session (dilarang per dok 2.0 BaseAgent→BaseNode)
  - forward setiap yielded `Event` ke WS sebagai JSON
- [ ] **4.4** Frontend `stream-viewer.tsx` mapping:
  - `event.author` → badge (agent/user/tool)
  - `event.content.parts` → render text / tool_call / tool_response
  - `event.node_info` → tampilkan node graph (fitur 2.0)
- [ ] **4.5** Test: full loop prompt → compile → save → start session → kirim message → terima `Event` chain → final response

---

## Phase 5 — UX: tampilkan katalog tool, sembunyikan YAML

**Goal:** YAML editor jadi optional; user awam tidak pernah lihat.

- [ ] **5.1** Komponen `<ToolCatalog />` di `apps/web/components/`:
  - panggil `GET /tools` saat mount, cache di Zustand
  - render grid card dengan name + description + input schema preview
- [ ] **5.2** Quickstart panel: di bawah textarea prompt, tampilkan thumbnail catalog (collapsible)
- [ ] **5.3** Setelah compile, tampilkan **Form view** sebagai default:
  - field `name`, `model` (dropdown), `instruction` (textarea), `tools` (multi-select dari catalog)
  - tombol "Advanced (YAML)" buka Monaco editor
- [ ] **5.4** Edit di Form view → langsung POST ke `PATCH /agents/{id}` (partial config)
- [ ] **5.5** Edit di YAML view → parse → POST → kalau invalid, highlight di Monaco

---

## Phase 6 — Dry-run sebelum save (opsional, recommended)

**Goal:** Catch agent yang langsung error sebelum user simpan.

- [ ] **6.1** Endpoint `POST /agents/dry-run` body = AgentConfig JSON:
  - build sementara Runner in-memory (tanpa persist session)
  - kirim sample input dari `config.dry_run_sample` (atau "say hello" default)
  - return `{ok: bool, events: [...], error: ...}` dengan timeout 10 detik
- [ ] **6.2** UI: tombol "Test" di form view → call dry-run → tampilkan event timeline mini
- [ ] **6.3** Disable tombol "Save" kalau dry-run gagal kecuali user klik "Save anyway"

---

## Phase 7 — (Fase berikutnya) Multi-agent / Graph workflow

**Goal:** Manfaatkan fitur khas ADK 2 (graph-based workflows) di UI.

- [ ] **7.1** Tambah dukungan `SequentialAgent` / `ParallelAgent` / `LoopAgent` di compiler prompt-instruction
- [ ] **7.2** UI node-editor sederhana (mungkin react-flow) untuk compose graph
- [ ] **7.3** Render `event.node_info` di stream-viewer sebagai breadcrumb node

---

## Migrasi dari MVP plan

| Item di MVP plan | Status setelah integrasi |
|---|---|
| `services/compiler.py` (Task 5) | **Diganti** oleh Phase 2 |
| `models/session.py` (Task 2) | **Diperluas** — tambah `session_events` table di Phase 4.1 |
| YAML schema custom | **Dihapus** — pakai AgentConfig |
| WS protocol custom | **Diganti** — forward ADK Event langsung |
| Monaco YAML editor (Task 9) | **Tetap, tapi jadi Advanced view** (Phase 5.3) |

---

## Risiko & mitigasi

- **ADK 2 baru GA (19 Mei 2026):** ekosistem masih hangat. Kalau ada blocker, pin ke `google-adk~=1.11` dulu — fitur Agent Config sudah ada sejak 1.11 (lihat [agents/config.md](../../adk/agents/config.md)). Migrasi ke 2.0 nanti tinggal `BaseAgent`→`BaseNode` refactor.
- **`response_format=json_schema` butuh provider yang support:** OpenAI ✅, Anthropic ✅ (lewat tool_use), Ollama parsial. Tambah fallback ke JSON-mode + regex repair untuk provider lemah.
- **Tool registry harus thread-safe:** karena FastAPI async; register sekali di startup, treat `TOOL_REGISTRY` sebagai immutable setelah `lifespan` startup selesai.
- **Session blob bisa besar:** tambah index parsial + retention policy (drop events > 30 hari) di Phase 4.
