// lib/api.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const API = API_BASE_URL

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

/**
 * POST /v1/agents — create new agent from a config dict (Phase 5B).
 * Returns the created agent or throws with detail on 422.
 */
export async function createAgentFromConfig(config: Record<string, unknown>) {
  const res = await fetch(`${API}/v1/agents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error("Failed to create agent") as Error & { status: number; detail: unknown }
    err.status = res.status
    err.detail = body.detail
    throw err
  }
  return res.json()
}

/**
 * PATCH /v1/agents/{id} — replace config for an existing agent (Phase 5B).
 * Returns the updated agent or throws with detail on 422.
 */
export async function patchAgent(agentId: string, config: Record<string, unknown>) {
  const res = await fetch(`${API}/v1/agents/${agentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error("Failed to patch agent") as Error & { status: number; detail: unknown }
    err.status = res.status
    err.detail = body.detail
    throw err
  }
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

// ---------------------------------------------------------------------------
// Phase 6: Dry-run
// ---------------------------------------------------------------------------

export interface DryRunResult {
  ok: boolean
  events: Record<string, unknown>[]
  error: string | null
  elapsed_ms: number | null
}

/**
 * POST /v1/agents/dry-run — build an in-memory runner, run one turn, return events.
 * Always resolves (never throws) — check `result.ok` for success/failure.
 */
export async function dryRunAgent(config: Record<string, unknown>): Promise<DryRunResult> {
  try {
    const res = await fetch(`${API}/v1/agents/dry-run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      return {
        ok: false,
        events: [],
        error: body.detail ?? `HTTP ${res.status}`,
        elapsed_ms: null,
      }
    }
    return res.json() as Promise<DryRunResult>
  } catch (err) {
    return {
      ok: false,
      events: [],
      error: err instanceof Error ? err.message : "Network error",
      elapsed_ms: null,
    }
  }
}
