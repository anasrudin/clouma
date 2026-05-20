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
