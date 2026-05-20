"use client"
import { useCallback } from "react"
import { useAgentStore } from "@/store/agent"
import { compileAgent, createAgent, createSession } from "@/lib/api"
import { connectSessionStream } from "@/lib/ws"
import { QuickstartPanel } from "@/components/quickstart-panel"
import { TemplateBrowser } from "@/components/template-browser"
import { YamlEditor } from "@/components/yaml-editor"
import { StreamViewer } from "@/components/stream-viewer"

export default function QuickstartPage() {
  const {
    yaml, agentId, sessionId,
    setYaml, setIsCompiling, setAgentId, setSessionId,
    addStreamEvent, clearStreamEvents, setSessionStatus,
    setCurrentStep,
  } = useAgentStore()

  const handleCompile = useCallback(async (prompt: string) => {
    setIsCompiling(true)
    setYaml("")
    try {
      await compileAgent(prompt, (token) => {
        useAgentStore.setState((s) => ({ yaml: s.yaml + token }))
      })
    } catch (e) {
      console.error("Compile error", e)
    } finally {
      setIsCompiling(false)
    }
  }, [setIsCompiling, setYaml])

  const handleTemplateSelect = useCallback((yaml: string, name: string) => {
    useAgentStore.setState({ yaml, agentName: name })
  }, [])

  const handleCreateAgent = useCallback(async (name: string, yamlStr: string) => {
    try {
      const agent = await createAgent(name, yamlStr)
      setAgentId(agent.id)
    } catch (e) {
      console.error("Create agent error", e)
    }
  }, [setAgentId])

  const handleStartSession = useCallback(async () => {
    if (!agentId) return
    clearStreamEvents()
    setSessionStatus("running")
    try {
      const session = await createSession(agentId)
      setSessionId(session.id)
      setCurrentStep(3)
      const disconnect = connectSessionStream(
        session.id,
        { agentId: agentId! },
        (data) => {
          const event = data as Parameters<typeof addStreamEvent>[0]
          addStreamEvent(event)
          if (event.type === "status") {
            if (event.status === "completed" || event.status === "failed") {
              setSessionStatus(event.status)
              disconnect()
            }
          }
        },
        () => setSessionStatus("completed")
      )
    } catch (e) {
      console.error("Session error", e)
      setSessionStatus("failed")
    }
  }, [agentId, clearStreamEvents, setSessionStatus, setSessionId, setCurrentStep, addStreamEvent])

  const showStream = sessionId !== null

  return (
    <div className="flex h-full">
      <div className="w-[42%] shrink-0">
        <QuickstartPanel onSubmit={handleCompile} />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        {showStream ? (
          <StreamViewer />
        ) : yaml ? (
          <YamlEditor onCreateAgent={handleCreateAgent} />
        ) : (
          <TemplateBrowser onSelect={handleTemplateSelect} />
        )}
        {agentId && !sessionId && (
          <div className="border-t border-white/[0.06] px-4 py-2.5 flex justify-end shrink-0">
            <button
              onClick={handleStartSession}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold px-4 py-1.5 rounded transition-colors"
            >
              Start session →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
