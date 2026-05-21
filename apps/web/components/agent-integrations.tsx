"use client"

import { useEffect, useState } from "react"
import { Plus, Trash2, KeyRound } from "lucide-react"
import {
  listAgentSecrets,
  upsertAgentSecret,
  deleteAgentSecret,
  type SecretDescriptor,
} from "@/lib/api"

const KNOWN_SERVICES = [
  { value: "telegram", label: "Telegram", keys: ["bot_token", "chat_id"] },
  { value: "confluence", label: "Confluence", keys: ["api_key", "base_url", "space_key"] },
  { value: "slack", label: "Slack", keys: ["webhook_url"] },
  { value: "custom", label: "Custom", keys: [] },
]

interface AddFormState {
  service: string
  keyName: string
  value: string
}

const EMPTY_FORM: AddFormState = { service: "telegram", keyName: "", value: "" }

export function AgentIntegrations({ agentId }: { agentId: string }) {
  const [secrets, setSecrets] = useState<SecretDescriptor[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState<AddFormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listAgentSecrets(agentId)
      .then(setSecrets)
      .catch(() => setError("Failed to load integrations"))
      .finally(() => setLoading(false))
  }, [agentId])

  const selectedService = KNOWN_SERVICES.find((s) => s.value === form.service)
  const suggestedKeys = selectedService?.keys ?? []

  async function handleSave() {
    if (!form.service || !form.keyName || !form.value) return
    setSaving(true)
    setError(null)
    try {
      const saved = await upsertAgentSecret(agentId, form.service, form.keyName, form.value)
      setSecrets((prev) => {
        const idx = prev.findIndex(
          (s) => s.service === saved.service && s.key_name === saved.key_name,
        )
        return idx >= 0
          ? prev.map((s, i) => (i === idx ? saved : s))
          : [...prev, saved]
      })
      setForm(EMPTY_FORM)
      setAdding(false)
    } catch {
      setError("Failed to save credential")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(service: string, keyName: string) {
    try {
      await deleteAgentSecret(agentId, service, keyName)
      setSecrets((prev) =>
        prev.filter((s) => !(s.service === service && s.key_name === keyName)),
      )
    } catch {
      setError("Failed to delete credential")
    }
  }

  if (loading) {
    return <p className="text-[10px] text-neutral-500 py-2">Loading integrations...</p>
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <KeyRound size={11} className="text-indigo-400" />
          <span className="text-[11px] font-semibold text-neutral-300">Integrations</span>
        </div>
        <button
          onClick={() => setAdding((v) => !v)}
          className="flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          <Plus size={10} />
          Add credential
        </button>
      </div>

      {error && <p className="text-[10px] text-red-400">{error}</p>}

      {secrets.length > 0 && (
        <div className="space-y-1">
          {secrets.map((s) => (
            <div
              key={`${s.service}-${s.key_name}`}
              className="flex items-center justify-between bg-white/[0.03] border border-white/[0.06] rounded px-2.5 py-1.5"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-[10px] font-mono text-indigo-300 shrink-0">{s.service}</span>
                <span className="text-[9px] text-neutral-500">·</span>
                <span className="text-[10px] text-neutral-400 truncate">{s.key_name}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-[9px] text-neutral-600 font-mono">••••••••</span>
                <button
                  onClick={() => handleDelete(s.service, s.key_name)}
                  className="text-neutral-600 hover:text-red-400 transition-colors"
                  aria-label={`Delete ${s.service} ${s.key_name}`}
                >
                  <Trash2 size={10} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {secrets.length === 0 && !adding && (
        <p className="text-[10px] text-neutral-600 py-1">No integrations configured.</p>
      )}

      {adding && (
        <div className="bg-white/[0.03] border border-white/[0.08] rounded p-2.5 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[9px] text-neutral-500 block mb-1">Service</label>
              <select
                value={form.service}
                onChange={(e) => setForm((f) => ({ ...f, service: e.target.value, keyName: "" }))}
                className="w-full bg-[#1a1a1e] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-neutral-200 outline-none"
              >
                {KNOWN_SERVICES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[9px] text-neutral-500 block mb-1">Key name</label>
              {suggestedKeys.length > 0 ? (
                <select
                  value={form.keyName}
                  onChange={(e) => setForm((f) => ({ ...f, keyName: e.target.value }))}
                  className="w-full bg-[#1a1a1e] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-neutral-200 outline-none"
                >
                  <option value="">Select key...</option>
                  {suggestedKeys.map((k) => (
                    <option key={k} value={k}>{k}</option>
                  ))}
                </select>
              ) : (
                <input
                  value={form.keyName}
                  onChange={(e) => setForm((f) => ({ ...f, keyName: e.target.value }))}
                  placeholder="e.g. api_key"
                  className="w-full bg-[#1a1a1e] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-neutral-200 placeholder:text-neutral-600 outline-none"
                />
              )}
            </div>
          </div>
          <div>
            <label className="text-[9px] text-neutral-500 block mb-1">Value</label>
            <input
              type="password"
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="Paste your secret value..."
              className="w-full bg-[#1a1a1e] border border-white/[0.08] rounded px-2 py-1 text-[10px] text-neutral-200 placeholder:text-neutral-600 outline-none"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => { setAdding(false); setForm(EMPTY_FORM) }}
              className="text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !form.service || !form.keyName || !form.value}
              className="text-[10px] px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded transition-colors"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
