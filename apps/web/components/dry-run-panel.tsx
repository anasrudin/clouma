"use client"
import { useState } from "react"
import { dryRunAgent, type DryRunResult } from "@/lib/api"
import type { AgentConfig } from "@/store/agent"
import { cn } from "@/lib/utils"

interface DryRunPanelProps {
  config: AgentConfig
  onResult: (result: DryRunResult) => void
}

export function DryRunPanel({ config, onResult }: DryRunPanelProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DryRunResult | null>(null)
  const [eventsOpen, setEventsOpen] = useState(false)

  const handleTest = async () => {
    setLoading(true)
    setResult(null)
    setEventsOpen(false)
    try {
      const r = await dryRunAgent(config as Record<string, unknown>)
      setResult(r)
      onResult(r)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-2 px-4 py-3 border-b border-white/[0.06] shrink-0">
      <div className="flex items-center gap-3">
        {/* Test button */}
        <button
          onClick={handleTest}
          disabled={loading}
          className={cn(
            "text-[10px] font-semibold px-3 py-1 rounded transition-colors",
            loading
              ? "bg-white/[0.06] text-neutral-500 cursor-not-allowed"
              : "bg-amber-600 hover:bg-amber-500 text-white",
          )}
        >
          {loading ? "Running test…" : "Test"}
        </button>

        {/* Loading spinner + label */}
        {loading && (
          <span className="text-[10px] text-neutral-500 animate-pulse">
            Running sample turn…
          </span>
        )}

        {/* Result badge */}
        {!loading && result !== null && (
          result.ok ? (
            <span className="text-[10px] text-emerald-400 font-medium">
              Test passed
              {result.elapsed_ms != null && (
                <span className="ml-1 text-neutral-500">({result.elapsed_ms}ms)</span>
              )}
            </span>
          ) : (
            <span className="text-[10px] text-red-400 font-medium truncate max-w-xs" title={result.error ?? undefined}>
              Test failed: {result.error}
            </span>
          )
        )}

        {/* Collapsible events toggle */}
        {!loading && result !== null && result.events.length > 0 && (
          <button
            onClick={() => setEventsOpen((v) => !v)}
            className="ml-auto text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            {eventsOpen ? "Hide events" : `Show events (${result.events.length})`}
          </button>
        )}
      </div>

      {/* Event timeline mini-panel */}
      {eventsOpen && result !== null && result.events.length > 0 && (
        <div className="mt-1 rounded border border-white/[0.06] bg-white/[0.02] max-h-48 overflow-y-auto">
          {result.events.map((evt, i) => {
            const author = String((evt as Record<string, unknown>).author ?? "agent")
            const content = (evt as Record<string, unknown>).content as
              | { parts?: { text?: string }[] }
              | undefined
            const text = content?.parts?.find((p) => p.text)?.text
            return (
              <div
                key={i}
                className="flex gap-2 px-2.5 py-1.5 border-b border-white/[0.04] last:border-0"
              >
                <span className="text-[9px] font-mono text-indigo-400 shrink-0 pt-px">
                  {author}
                </span>
                {text ? (
                  <p className="text-[10px] text-neutral-300 leading-relaxed line-clamp-2">
                    {text}
                  </p>
                ) : (
                  <p className="text-[10px] text-neutral-600 italic">
                    {JSON.stringify(evt).slice(0, 80)}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
