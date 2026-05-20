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
