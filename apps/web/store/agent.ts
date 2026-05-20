// store/agent.ts
import { create } from "zustand"

export type StreamEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; input: string }
  | { type: "tool_result"; tool: string; output: string }
  | { type: "checkpoint"; step: number; state: string }
  | { type: "status"; status: "running" | "waiting" | "completed" | "failed" }
  | { type: "error"; message: string }

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
