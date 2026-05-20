"use client"
import dynamic from "next/dynamic"
import { useAgentStore } from "@/store/agent"
import { cn } from "@/lib/utils"
import yaml from "yaml"

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false })

export function YamlEditor({
  onCreateAgent,
}: {
  onCreateAgent: (name: string, yamlStr: string) => void
}) {
  const { yaml: yamlStr, setYaml, activeTab, setActiveTab, agentId, agentName, setAgentName } =
    useAgentStore()

  const jsonValue = (() => {
    try {
      return JSON.stringify(yaml.parse(yamlStr), null, 2)
    } catch {
      return "{}"
    }
  })()

  const displayValue = activeTab === "yaml" ? yamlStr : jsonValue
  const language = activeTab === "yaml" ? "yaml" : "json"

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-4 px-4 py-2 border-b border-white/[0.06] shrink-0">
        {(["yaml", "json"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "text-[11px] font-medium pb-1 transition-colors uppercase tracking-wide",
              activeTab === tab
                ? "text-violet-400 border-b border-violet-400"
                : "text-neutral-500 hover:text-neutral-300"
            )}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {yamlStr ? (
          <MonacoEditor
            value={displayValue}
            language={language}
            theme="vs-dark"
            onChange={(v) => {
              if (activeTab === "yaml") setYaml(v ?? "")
            }}
            options={{
              fontSize: 12,
              lineHeight: 1.7,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: "on",
              readOnly: activeTab === "json",
              padding: { top: 12, bottom: 12 },
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-neutral-600 text-[12px]">
            Type a prompt or select a template to generate your agent spec.
          </div>
        )}
      </div>
      {yamlStr && !agentId && (
        <div className="border-t border-white/[0.06] px-4 py-2.5 flex items-center gap-3 shrink-0">
          <input
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Agent name..."
            className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded px-2.5 py-1.5 text-[11px] text-neutral-200 placeholder:text-neutral-600 outline-none"
          />
          <button
            onClick={() => onCreateAgent(agentName || "my-agent", yamlStr)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium px-3 py-1.5 rounded transition-colors shrink-0"
          >
            Create agent
          </button>
        </div>
      )}
      {agentId && (
        <div className="border-t border-white/[0.06] px-4 py-2 shrink-0">
          <p className="text-[10px] text-emerald-500">
            ✓ Agent created — proceed to Configure environment
          </p>
        </div>
      )}
    </div>
  )
}
