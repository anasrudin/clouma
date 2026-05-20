"use client"
import { useRef } from "react"
import { ArrowUp } from "lucide-react"
import { useAgentStore } from "@/store/agent"
import { cn } from "@/lib/utils"

export function QuickstartPanel({ onSubmit }: { onSubmit: (prompt: string) => void }) {
  const { prompt, setPrompt, isCompiling } = useAgentStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      if (prompt.trim() && !isCompiling) onSubmit(prompt.trim())
    }
  }

  return (
    <div className="flex flex-col h-full border-r border-white/[0.06]">
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <h2 className="text-[15px] font-semibold text-white mb-2">
          What do you want to build?
        </h2>
        <p className="text-[11px] text-neutral-500">
          Describe your agent or start with a template.
        </p>
      </div>
      <div className="p-3 border-t border-white/[0.06] shrink-0">
        <div className="flex items-end gap-2 bg-[#1a1a1e] border border-white/[0.08] rounded-lg px-3 py-2.5">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your agent..."
            rows={1}
            className="flex-1 bg-transparent text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none resize-none max-h-32 leading-relaxed"
            style={{ minHeight: "20px" }}
          />
          <button
            onClick={() => prompt.trim() && !isCompiling && onSubmit(prompt.trim())}
            disabled={!prompt.trim() || isCompiling}
            className={cn(
              "w-6 h-6 rounded flex items-center justify-center shrink-0 transition-colors",
              prompt.trim() && !isCompiling
                ? "bg-indigo-600 hover:bg-indigo-500 text-white"
                : "bg-white/[0.06] text-neutral-600 cursor-not-allowed"
            )}
          >
            <ArrowUp size={13} />
          </button>
        </div>
        {isCompiling && (
          <p className="text-[10px] text-indigo-400 mt-1.5 text-center">
            Compiling agent spec...
          </p>
        )}
      </div>
    </div>
  )
}
