"use client"
import { useRef, useState } from "react"
import { ArrowUp, ChevronDown, ChevronRight } from "lucide-react"
import { useAgentStore } from "@/store/agent"
import { cn } from "@/lib/utils"
import { ToolCatalog } from "@/components/tool-catalog"

const EXAMPLE_PROMPTS = [
  "Monitor trending AI news every morning and send a summary to Telegram",
  "Research competitor pricing weekly and generate a PDF report",
  "Fetch the latest RSS articles from Hacker News and summarize the top 5",
  "Every day at 9am, scrape my website's uptime and alert me if it's down",
  "Given a YouTube URL, transcribe the video and write a structured blog post",
]

const GREETINGS = new Set([
  "halo", "hallo", "hello", "hi", "hey", "test", "tes", "coba",
  "hai", "yo", "sup", "ping", "ok", "okay", "oke",
])

function isVaguePrompt(text: string): boolean {
  const clean = text.trim().toLowerCase().replace(/[^a-z0-9 ]/g, "")
  if (clean.split(/\s+/).every((w) => GREETINGS.has(w))) return true
  if (clean.length < 20) return true
  return false
}

export function QuickstartPanel({ onSubmit }: { onSubmit: (prompt: string) => void }) {
  const { prompt, setPrompt, isCompiling, tools } = useAgentStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [vagueError, setVagueError] = useState(false)

  const handleSubmit = () => {
    const trimmed = prompt.trim()
    if (!trimmed || isCompiling) return
    if (isVaguePrompt(trimmed)) {
      setVagueError(true)
      textareaRef.current?.focus()
      return
    }
    setVagueError(false)
    onSubmit(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const fillExample = (ex: string) => {
    setPrompt(ex)
    setVagueError(false)
    textareaRef.current?.focus()
  }

  return (
    <div className="flex flex-col h-full border-r border-white/[0.06]">
      {/* Center area: heading + examples */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 gap-4">
        <div className="text-center">
          <h2 className="text-[15px] font-semibold text-white mb-1">
            What do you want to build?
          </h2>
          <p className="text-[11px] text-neutral-500">
            Describe your agent or pick an example below.
          </p>
        </div>

        {/* Example prompts */}
        <div className="flex flex-col gap-1.5 w-full max-w-sm">
          {EXAMPLE_PROMPTS.map((ex) => (
            <button
              key={ex}
              onClick={() => fillExample(ex)}
              className="text-left text-[10.5px] text-neutral-400 hover:text-neutral-200 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.12] rounded-md px-3 py-2 transition-colors leading-relaxed"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Input area */}
      <div className="p-3 border-t border-white/[0.06] shrink-0">
        <div className={cn(
          "flex items-end gap-2 bg-[#1a1a1e] border rounded-lg px-3 py-2.5 transition-colors",
          vagueError ? "border-amber-500/50" : "border-white/[0.08]",
        )}>
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value)
              if (vagueError) setVagueError(false)
            }}
            onKeyDown={handleKeyDown}
            placeholder="Describe what your agent should do..."
            rows={1}
            className="flex-1 bg-transparent text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none resize-none max-h-32 leading-relaxed"
            style={{ minHeight: "20px" }}
          />
          <button
            onClick={handleSubmit}
            disabled={!prompt.trim() || isCompiling}
            className={cn(
              "w-6 h-6 rounded flex items-center justify-center shrink-0 transition-colors",
              prompt.trim() && !isCompiling
                ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                : "bg-white/[0.06] text-neutral-600 cursor-not-allowed",
            )}
          >
            <ArrowUp size={13} />
          </button>
        </div>

        {vagueError && (
          <p className="text-[10px] text-amber-400 mt-1.5 px-1">
            Describe what your agent should actually do — be specific about the task, schedule, or output.
          </p>
        )}

        {isCompiling && (
          <p className="text-[10px] text-indigo-400 mt-1.5 text-center">
            Compiling agent spec...
          </p>
        )}

        {/* Collapsible tool catalog */}
        <div className="mt-2">
          <button
            onClick={() => setCatalogOpen((o) => !o)}
            aria-expanded={catalogOpen}
            className="flex items-center gap-1 text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors w-full"
          >
            {catalogOpen ? (
              <ChevronDown size={10} className="shrink-0" aria-hidden="true" />
            ) : (
              <ChevronRight size={10} className="shrink-0" aria-hidden="true" />
            )}
            <span>Available tools ({tools.length})</span>
          </button>
          {catalogOpen && (
            <div className="mt-1.5 max-h-48 overflow-y-auto">
              <ToolCatalog compact />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
