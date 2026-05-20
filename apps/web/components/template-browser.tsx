"use client"
import { useState } from "react"
import { Search } from "lucide-react"

const TEMPLATES = [
  { id: "blank", name: "Blank agent config", desc: "A blank starting point with the core toolset.", yaml: "name: my-agent\ndescription: My custom agent\nmodel: llama3.2\nschedule: null\ntools:\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "researcher", name: "Deep researcher", desc: "Conducts multi-step web research with source synthesis and citations.", yaml: "name: deep-researcher\ndescription: Conducts multi-step web research\nmodel: llama3.2\nschedule: null\ntools:\n  - web_search\n  - memory_store\n  - file_write\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 600" },
  { id: "support", name: "Support agent", desc: "Answers customer questions from your docs and knowledge base.", yaml: "name: support-agent\ndescription: Answers customer questions from docs\nmodel: llama3.2\nschedule: null\ntools:\n  - memory_store\n  - api_call\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "incident", name: "Incident commander", desc: "Triages a Sentry alert, opens a Linear incident ticket.", yaml: "name: incident-commander\ndescription: Triages alerts and opens Linear tickets\nmodel: llama3.2\nschedule: null\ntools:\n  - api_call\n  - slack_send\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "contract", name: "Contract tracker", desc: "Extracts clauses, sets deadline reminders, tracks obligations.", yaml: "name: contract-tracker\ndescription: Extracts clauses and tracks obligations\nmodel: llama3.2\nschedule: null\ntools:\n  - file_read\n  - memory_store\n  - email_send\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 300" },
  { id: "analyst", name: "Data analyst", desc: "Load, explore, and visualize data; build reports from datasets.", yaml: "name: data-analyst\ndescription: Load and visualize data\nmodel: llama3.2\nschedule: null\ntools:\n  - file_read\n  - code_exec\n  - memory_store\nmemory:\n  type: episodic\n  backend: qdrant\nruntime:\n  sandbox: browser\n  timeout: 600" },
]

export function TemplateBrowser({ onSelect }: { onSelect: (yaml: string, name: string) => void }) {
  const [search, setSearch] = useState("")

  const filtered = TEMPLATES.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.desc.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-white/[0.06] shrink-0">
        <p className="text-[13px] font-semibold text-white mb-2">Browse templates</p>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded px-2.5 py-1.5">
          <Search size={12} className="text-neutral-500 shrink-0" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates"
            className="bg-transparent text-[11px] text-neutral-300 placeholder:text-neutral-600 outline-none flex-1"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 gap-1.5 content-start">
        {filtered.map((t) => (
          <button
            key={t.id}
            onClick={() => onSelect(t.yaml, t.name)}
            className="text-left bg-white/[0.03] border border-white/[0.06] rounded-md p-2.5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-colors group"
          >
            <p className="text-[10.5px] font-semibold text-neutral-200 mb-1 group-hover:text-white">
              {t.name}
            </p>
            <p className="text-[10px] text-neutral-600 leading-relaxed">{t.desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
