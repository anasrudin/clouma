"use client"
import { useEffect, useState } from "react"
import { listAgents } from "@/lib/api"
import { formatDistanceToNow } from "date-fns"

interface Agent {
  id: string
  name: string
  status: string
  created_at: string
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listAgents()
      .then(setAgents)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-[15px] font-semibold text-white mb-4">Agents</h1>
      {loading ? (
        <p className="text-[11px] text-neutral-600">Loading...</p>
      ) : agents.length === 0 ? (
        <p className="text-[11px] text-neutral-600">
          No agents yet. Go to{" "}
          <a href="/quickstart" className="text-violet-400 underline">
            Quickstart
          </a>{" "}
          to create one.
        </p>
      ) : (
        <table className="w-full text-[11px]">
          <thead>
            <tr className="border-b border-white/[0.06] text-left text-neutral-500">
              <th className="pb-2 font-medium">Name</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                <td className="py-2 text-neutral-200 font-mono">{a.name}</td>
                <td className="py-2">
                  <span className="bg-emerald-500/10 text-emerald-400 text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase">
                    {a.status}
                  </span>
                </td>
                <td className="py-2 text-neutral-500">
                  {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
