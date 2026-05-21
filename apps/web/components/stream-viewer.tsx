"use client"
import { useRef, useState } from "react"
import { ArrowUp } from "lucide-react"
/**
 * StreamViewer — renders events from the agent execution stream.
 *
 * Handles two event shapes:
 *   1. Legacy StreamEvent union (mock/UI events): token | tool_call | tool_result
 *      | checkpoint | status | error
 *   2. ADK 2.0 native events ({ type: "adk_event", raw: AdkEvent }): events
 *      forwarded as-is from runner.run_async() via the /sessions/{id}/ws endpoint.
 *
 * The component reads from useAgentStore (Zustand). Real WebSocket wiring is
 * deferred to Phase 5 — for now, events are injected via the store's
 * addStreamEvent() action.
 */
import { useAgentStore, StreamEvent, AdkEvent, AdkPart } from "@/store/agent"
import { cn } from "@/lib/utils"

// ---------------------------------------------------------------------------
// Author badge
// ---------------------------------------------------------------------------

function AuthorBadge({ author }: { author?: string }) {
  if (!author) return null
  const isUser = author === "user"
  const isTool = author !== "user" && author !== "model"
  return (
    <span
      className={cn(
        "text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded shrink-0",
        isUser
          ? "bg-blue-500/10 text-blue-400"
          : isTool
          ? "bg-violet-500/10 text-violet-400"
          : "bg-neutral-500/10 text-neutral-400"
      )}
    >
      {author}
    </span>
  )
}

// ---------------------------------------------------------------------------
// ADK Part renderers
// ---------------------------------------------------------------------------

function TextPart({ text }: { text: string }) {
  return <span className="text-neutral-300 text-[11px] whitespace-pre-wrap">{text}</span>
}

function FunctionCallPart({ part }: { part: { id?: string; name: string; args: Record<string, unknown> } }) {
  const argsStr = JSON.stringify(part.args ?? {}, null, 0)
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-violet-400 text-[10px] font-mono shrink-0">→ {part.name}</span>
      <span className="text-neutral-500 text-[10px] font-mono truncate">{argsStr}</span>
    </div>
  )
}

function FunctionResponsePart({ part }: { part: { id?: string; name: string; response: Record<string, unknown> } }) {
  const respStr = JSON.stringify(part.response ?? {}, null, 0)
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-emerald-400 text-[10px] font-mono shrink-0">← {part.name}</span>
      <span className="text-neutral-400 text-[10px] truncate">{respStr}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// ADK Event row
// ---------------------------------------------------------------------------

function AdkEventRow({ event }: { event: AdkEvent }) {
  const parts = event.content?.parts ?? []
  const hasContent = parts.length > 0
  const nodeLabel = event.node_info?.node_name

  return (
    <div className="py-1">
      {/* Node info breadcrumb (ADK 2.0) */}
      {nodeLabel && (
        <div className="text-[9px] text-neutral-600 mb-0.5 font-mono">{nodeLabel}</div>
      )}

      {/* Author + content */}
      {hasContent && (
        <div className="flex items-start gap-2">
          <AuthorBadge author={event.author} />
          <div className="flex flex-col gap-0.5 min-w-0 flex-1">
            {parts.map((part, i) => {
              if ("text" in part && part.text !== "") {
                return <TextPart key={i} text={part.text} />
              }
              if ("function_call" in part) {
                return <FunctionCallPart key={i} part={part.function_call} />
              }
              if ("function_response" in part) {
                return <FunctionResponsePart key={i} part={part.function_response} />
              }
              return null
            })}
          </div>
        </div>
      )}

      {/* Error message */}
      {event.error_message && (
        <div className="text-red-400 text-[10px] font-mono">{event.error_message}</div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Legacy event row (unchanged behaviour)
// ---------------------------------------------------------------------------

function LegacyEventRow({ event }: { event: StreamEvent }) {
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
  if (event.type === "error") {
    return (
      <div className="text-red-400 text-[10px] font-mono py-0.5">{event.message}</div>
    )
  }
  return null
}

// ---------------------------------------------------------------------------
// Unified EventRow dispatcher
// ---------------------------------------------------------------------------

function EventRow({ event }: { event: StreamEvent }) {
  if (event.type === "adk_event") {
    return <AdkEventRow event={event.raw} />
  }
  return <LegacyEventRow event={event} />
}

// ---------------------------------------------------------------------------
// StreamViewer
// ---------------------------------------------------------------------------

export function StreamViewer({ onSend }: { onSend?: (text: string) => void }) {
  const { streamEvents, sessionStatus } = useAgentStore()
  const [input, setInput] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const handleSend = () => {
    const text = input.trim()
    if (!text || !onSend) return
    onSend(text)
    setInput("")
  }

  if (streamEvents.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 flex items-center justify-center text-neutral-600 text-[11px]">
          Starting session…
        </div>
        {onSend && <ChatInput input={input} setInput={setInput} inputRef={inputRef} onSend={handleSend} />}
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
        {streamEvents.map((e, i) => {
          const key = e.type === "adk_event" ? (e.raw.id ?? i) : i
          return <EventRow key={key} event={e} />
        })}
        <div ref={bottomRef} />
      </div>
      {onSend && (
        <ChatInput input={input} setInput={setInput} inputRef={inputRef} onSend={handleSend} />
      )}
    </div>
  )
}

function ChatInput({
  input,
  setInput,
  inputRef,
  onSend,
}: {
  input: string
  setInput: (v: string) => void
  inputRef: React.RefObject<HTMLInputElement>
  onSend: () => void
}) {
  return (
    <div className="px-3 py-2.5 border-t border-white/[0.06] shrink-0">
      <div className="flex items-center gap-2 bg-[#1a1a1e] border border-white/[0.08] rounded-lg px-3 py-2">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend() } }}
          placeholder="Send a message to the agent..."
          className="flex-1 bg-transparent text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none"
        />
        <button
          onClick={onSend}
          disabled={!input.trim()}
          className={cn(
            "w-6 h-6 rounded flex items-center justify-center shrink-0 transition-colors",
            input.trim()
              ? "bg-indigo-600 hover:bg-indigo-500 text-white"
              : "bg-white/[0.06] text-neutral-600 cursor-not-allowed",
          )}
        >
          <ArrowUp size={13} />
        </button>
      </div>
    </div>
  )
}
