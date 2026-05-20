// store/agent.ts
import { create } from "zustand"

// ---------------------------------------------------------------------------
// Legacy StreamEvent union (UI mock events — kept for backward compatibility)
// ---------------------------------------------------------------------------

export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; input: string }
  | { type: "tool_result"; tool: string; output: string }
  | { type: "checkpoint"; step: number; state: string }
  | { type: "status"; status: "running" | "waiting" | "completed" | "failed" }
  | { type: "error"; message: string }
  // ADK 2.0 native event — forwarded as-is from runner.run_async()
  | { type: "adk_event"; raw: AdkEvent }

// ---------------------------------------------------------------------------
// ADK 2.0 Event shape (subset of fields returned by event.model_dump())
// ---------------------------------------------------------------------------

export type AdkPart =
  | { text: string }
  | { function_call: { id?: string; name: string; args: Record<string, unknown> } }
  | { function_response: { id?: string; name: string; response: Record<string, unknown> } }

export interface AdkContent {
  role?: string
  parts?: AdkPart[]
}

export interface AdkNodeInfo {
  /** ADK 2.0 node graph breadcrumb, e.g. "root.sub_agent.tool_node" */
  node_name?: string
  [key: string]: unknown
}

export interface AdkEvent {
  id?: string
  author?: string
  content?: AdkContent
  actions?: {
    state_delta?: Record<string, unknown>
    [key: string]: unknown
  }
  timestamp?: number
  node_info?: AdkNodeInfo
  turn_complete?: boolean
  partial?: boolean
  error_message?: string
}

export interface AgentStore {
  prompt: string
  yaml: string
  agentName: string
  activeTab: "yaml" | "json"
  isCompiling: boolean
  agentId: string | null
  sessionId: string | null
  streamEvents: StreamEvent[]
  sessionStatus: "idle" | "running" | "completed" | "failed"
  currentStep: 1 | 2 | 3 | 4
  setPrompt: (p: string) => void
  setYaml: (y: string) => void
  setAgentName: (n: string) => void
  setActiveTab: (t: "yaml" | "json") => void
  setIsCompiling: (v: boolean) => void
  setAgentId: (id: string) => void
  setSessionId: (id: string) => void
  addStreamEvent: (e: StreamEvent) => void
  clearStreamEvents: () => void
  setSessionStatus: (s: "idle" | "running" | "completed" | "failed") => void
  setCurrentStep: (s: 1 | 2 | 3 | 4) => void
  reset: () => void
}

const initialState = {
  prompt: "",
  yaml: "",
  agentName: "",
  activeTab: "yaml" as const,
  isCompiling: false,
  agentId: null,
  sessionId: null,
  streamEvents: [],
  sessionStatus: "idle" as const,
  currentStep: 1 as const,
}

export const useAgentStore = create<AgentStore>((set) => ({
  ...initialState,
  setPrompt: (prompt) => set({ prompt }),
  setYaml: (yaml) => set({ yaml }),
  setAgentName: (agentName) => set({ agentName }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setIsCompiling: (isCompiling) => set({ isCompiling }),
  setAgentId: (agentId) => set({ agentId, currentStep: 2 }),
  setSessionId: (sessionId) => set({ sessionId, currentStep: 3 }),
  addStreamEvent: (e) => set((s) => ({ streamEvents: [...s.streamEvents, e] })),
  clearStreamEvents: () => set({ streamEvents: [] }),
  setSessionStatus: (sessionStatus) => set({ sessionStatus }),
  setCurrentStep: (currentStep) => set({ currentStep }),
  reset: () => set(initialState),
}))
