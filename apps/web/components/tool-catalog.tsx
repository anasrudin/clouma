"use client"
import { useEffect } from "react"
import { useAgentStore } from "@/store/agent"
import type { ToolDescriptor } from "@/store/agent"

interface ToolCatalogProps {
  /** Compact variant for embedding inside the quickstart panel */
  compact?: boolean
}

function ToolCard({ tool, compact }: { tool: ToolDescriptor; compact?: boolean }) {
  const params = Object.entries(tool.input_schema?.properties ?? {})
  const required = new Set(tool.input_schema?.required ?? [])

  return (
    <div className="text-left bg-white/[0.03] border border-white/[0.06] rounded-md p-2.5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-colors">
      <p className="text-[10.5px] font-mono font-semibold text-indigo-300 mb-1 truncate">
        {tool.name}
      </p>
      {!compact && tool.description && (
        <p className="text-[10px] text-neutral-500 leading-relaxed mb-1.5 line-clamp-2">
          {tool.description}
        </p>
      )}
      {params.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {params.slice(0, compact ? 3 : 6).map(([name]) => (
            <span
              key={name}
              className={`text-[9px] px-1 py-0.5 rounded border ${
                required.has(name)
                  ? "bg-indigo-950/60 border-indigo-800/50 text-indigo-300 font-semibold"
                  : "bg-white/[0.04] border-white/[0.08] text-neutral-500"
              }`}
            >
              {required.has(name) ? `${name}*` : name}
            </span>
          ))}
          {params.length > (compact ? 3 : 6) && (
            <span className="text-[9px] text-neutral-600">
              +{params.length - (compact ? 3 : 6)} more
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-md p-2.5 animate-pulse">
      <div className="h-2.5 w-24 bg-white/[0.08] rounded mb-2" />
      <div className="h-2 w-full bg-white/[0.05] rounded mb-1" />
      <div className="h-2 w-3/4 bg-white/[0.05] rounded" />
    </div>
  )
}

export function ToolCatalog({ compact = false }: ToolCatalogProps) {
  const { tools, toolsLoaded, loadTools } = useAgentStore()

  useEffect(() => {
    loadTools()
  }, [loadTools])

  if (!toolsLoaded) {
    return (
      <div className={`grid gap-1.5 ${compact ? "grid-cols-2" : "grid-cols-2 md:grid-cols-3"}`}>
        {Array.from({ length: compact ? 4 : 6 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    )
  }

  if (tools.length === 0) {
    return (
      <p className="text-[10px] text-neutral-600 text-center py-3">
        No tools available
      </p>
    )
  }

  return (
    <div className={`grid gap-1.5 ${compact ? "grid-cols-2" : "grid-cols-2 md:grid-cols-3"}`}>
      {tools.map((tool) => (
        <ToolCard key={tool.name} tool={tool} compact={compact} />
      ))}
    </div>
  )
}
