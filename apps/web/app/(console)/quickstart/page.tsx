"use client"
import { useCallback, useEffect, useRef, useState } from "react"
import yaml from "yaml"
import { useAgentStore } from "@/store/agent"
import { compileAgent, createAgentFromConfig, patchAgent, type DryRunResult } from "@/lib/api"
import { connectSessionStream, type SessionConnection } from "@/lib/ws"
import { QuickstartPanel } from "@/components/quickstart-panel"
import { TemplateBrowser } from "@/components/template-browser"
import { YamlEditor } from "@/components/yaml-editor"
import { StreamViewer } from "@/components/stream-viewer"
import { AgentFormView } from "@/components/agent-form-view"
import { DryRunPanel } from "@/components/dry-run-panel"
import { cn } from "@/lib/utils"
import type { AgentConfig, ValidationDelta } from "@/store/agent"

// ---------------------------------------------------------------------------
// View mode toggle classes
// ---------------------------------------------------------------------------

const toggleBtn =
  "text-[10px] font-medium px-2.5 py-1 rounded transition-colors"
const toggleActive =
  "bg-indigo-600 text-white"
const toggleInactive =
  "text-neutral-500 hover:text-neutral-300"

export default function QuickstartPage() {
  const {
    yaml: yamlStr,
    agentId,
    sessionId,
    tools,
    skills,
    compiledConfig,
    validationErrors,
    setYaml,
    setIsCompiling,
    setAgentId,
    setSessionId,
    addStreamEvent,
    clearStreamEvents,
    setSessionStatus,
    setCurrentStep,
    setCompiledConfig,
    setValidationErrors,
    loadTools,
    loadSkills,
  } = useAgentStore()

  // "form" is the default view after compile; "yaml" shows Monaco
  const [viewMode, setViewMode] = useState<"form" | "yaml">("form")
  const [yamlError, setYamlError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  // Phase 6: dry-run result + "save anyway" override
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null)
  const [saveAnyway, setSaveAnyway] = useState(false)
  const sessionConnRef = useRef<SessionConnection | null>(null)

  // After a failed dry-run, Save is disabled unless the user checks "Save anyway".
  // Before any test (dryRunResult === null), Save works normally.
  const dryRunBlocking = dryRunResult !== null && !dryRunResult.ok && !saveAnyway

  // Ensure tool + skill catalogs are loaded for the form view
  useEffect(() => {
    loadTools()
    loadSkills()
  }, [loadTools, loadSkills])


  // ---------------------------------------------------------------------------
  // Compile handler: SSE stream → result.config → compiledConfig
  // ---------------------------------------------------------------------------

  const handleCompile = useCallback(
    async (prompt: string) => {
      setIsCompiling(true)
      setYaml("")
      setCompiledConfig(null)
      setValidationErrors(null)
      setYamlError(null)
      setDryRunResult(null)
      setSaveAnyway(false)
      try {
        const result = await compileAgent(prompt, (phase) => {
          console.log("[compile] phase:", phase)
        })
        // Use result.config directly — no YAML round-trip needed
        setCompiledConfig(result.config)
        // Populate the YAML editor view by serializing the config
        try {
          const yamlStr = yaml.stringify(result.config)
          setYaml(yamlStr)
        } catch {
          // best-effort
        }
        setViewMode("form") // default to form view after compile
        setIsDirty(true)
      } catch (e) {
        console.error("Compile error", e)
        const msg = e instanceof Error ? e.message : "Compile failed"
        setYamlError(msg)
        setViewMode("yaml")
      } finally {
        setIsCompiling(false)
      }
    },
    [setIsCompiling, setYaml, setCompiledConfig, setValidationErrors],
  )

  const handleTemplateSelect = useCallback(
    (yamlContent: string, name: string) => {
      useAgentStore.setState({ yaml: yamlContent, agentName: name })
      setDryRunResult(null)
      setSaveAnyway(false)
      try {
        const parsed = yaml.parse(yamlContent) as AgentConfig
        setCompiledConfig(parsed)
        setViewMode("form")
        setIsDirty(true)
      } catch {
        setCompiledConfig(null)
        setViewMode("yaml")
      }
    },
    [setCompiledConfig, setDryRunResult, setSaveAnyway],
  )

  // ---------------------------------------------------------------------------
  // Form view onChange: keep compiledConfig + yaml in sync
  // ---------------------------------------------------------------------------

  const handleFormChange = useCallback(
    (next: AgentConfig) => {
      setCompiledConfig(next)
      setValidationErrors(null)
      setIsDirty(true)
      // Keep yaml store in sync so switching to YAML view is consistent
      try {
        const yamlContent = yaml.stringify(next)
        setYaml(yamlContent)
      } catch {
        // best-effort
      }
    },
    [setCompiledConfig, setValidationErrors, setYaml],
  )

  // ---------------------------------------------------------------------------
  // Save flow: POST (new) or PATCH (existing)
  // ---------------------------------------------------------------------------

  const handleSave = useCallback(async () => {
    if (!compiledConfig) return
    setIsSaving(true)
    setValidationErrors(null)
    setYamlError(null)
    try {
      const configPayload = compiledConfig as Record<string, unknown>
      if (agentId) {
        await patchAgent(agentId, configPayload)
      } else {
        const created = await createAgentFromConfig(configPayload)
        setAgentId(created.id)
      }
      setIsDirty(false)
    } catch (e: unknown) {
      const apiErr = e as { status?: number; detail?: unknown; message?: string }
      if (apiErr?.status === 422) {
        const detail = apiErr.detail as {
          message?: string
          delta?: ValidationDelta
        } | null
        if (detail?.delta) {
          setValidationErrors(detail.delta)
        }
        const msg = detail?.message ?? "Validation failed"
        setYamlError(msg)
      } else if (apiErr?.status === 409) {
        setYamlError("An agent with this name already exists. Choose a different name.")
      } else {
        console.error("Save error", e)
        setYamlError(apiErr?.message ?? "Save failed. Try again.")
      }
    } finally {
      setIsSaving(false)
    }
  }, [compiledConfig, agentId, setAgentId, setValidationErrors])

  // ---------------------------------------------------------------------------
  // Legacy create agent handler (from YamlEditor bottom bar)
  // ---------------------------------------------------------------------------

  const handleCreateAgent = useCallback(
    async (name: string, yamlContent: string) => {
      try {
        let config: Record<string, unknown>
        try {
          config = yaml.parse(yamlContent) as Record<string, unknown>
        } catch {
          config = { name, yaml_config: yamlContent }
        }
        const created = await createAgentFromConfig(config)
        setAgentId(created.id)
      } catch (e) {
        console.error("Create agent error", e)
      }
    },
    [setAgentId],
  )

  const handleStartSession = useCallback(async () => {
    if (!agentId) return
    clearStreamEvents()
    setSessionStatus("running")
    try {
      const { createSession } = await import("@/lib/api")
      const session = await createSession(agentId)
      setSessionId(session.id)
      setCurrentStep(3)
      const conn = connectSessionStream(
        session.id,
        { agentId: agentId! },
        (data) => {
          const event = data as Parameters<typeof addStreamEvent>[0]
          addStreamEvent(event)
          if (event.type === "status") {
            if (event.status === "completed" || event.status === "failed") {
              setSessionStatus(event.status)
              conn.disconnect()
              sessionConnRef.current = null
            }
          }
        },
        () => {
          setSessionStatus("completed")
          sessionConnRef.current = null
        },
      )
      sessionConnRef.current = conn
      // Auto-send initial trigger so the agent begins running immediately
      setTimeout(() => conn.send("Execute your task."), 300)
    } catch (e) {
      console.error("Session error", e)
      setSessionStatus("failed")
    }
  }, [
    agentId,
    clearStreamEvents,
    setSessionStatus,
    setSessionId,
    setCurrentStep,
    addStreamEvent,
  ])

  const showStream = sessionId !== null
  const hasContent = yamlStr.trim().length > 0

  return (
    <div className="flex h-full">
      <div className="w-[42%] shrink-0">
        <QuickstartPanel onSubmit={handleCompile} />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        {showStream ? (
          <StreamViewer onSend={(text) => sessionConnRef.current?.send(text)} />
        ) : hasContent ? (
          <>
            {/* View mode toggle header */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.06] shrink-0">
              <span className="text-[10px] text-neutral-500">Editor:</span>
              <div className="flex bg-white/[0.04] rounded p-0.5 gap-0.5">
                <button
                  onClick={() => {
                    // When switching back to form, re-parse current YAML store value
                    if (viewMode === "yaml" && yamlStr) {
                      try {
                        const parsed = yaml.parse(yamlStr) as AgentConfig
                        setCompiledConfig(parsed)
                        setYamlError(null)
                      } catch (parseErr) {
                        setYamlError(
                          parseErr instanceof Error
                            ? parseErr.message
                            : "YAML parse error",
                        )
                        // Stay in yaml view if the YAML is invalid
                        return
                      }
                    }
                    setViewMode("form")
                  }}
                  className={cn(
                    toggleBtn,
                    viewMode === "form" ? toggleActive : toggleInactive,
                  )}
                >
                  Form
                </button>
                <button
                  onClick={() => setViewMode("yaml")}
                  className={cn(
                    toggleBtn,
                    viewMode === "yaml" ? toggleActive : toggleInactive,
                  )}
                >
                  Advanced (YAML)
                </button>
              </div>
              {/* Save button */}
              {compiledConfig && !agentId && (
                <div className="ml-auto flex items-center gap-2">
                  {dryRunBlocking && (
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={saveAnyway}
                        onChange={(e) => setSaveAnyway(e.target.checked)}
                        className="accent-indigo-500"
                      />
                      <span className="text-[10px] text-neutral-500">Save anyway</span>
                    </label>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={!isDirty || isSaving || dryRunBlocking}
                    className={cn(
                      "text-[10px] font-semibold px-3 py-1 rounded transition-colors",
                      !isDirty || isSaving || dryRunBlocking
                        ? "bg-white/[0.06] text-neutral-500 cursor-not-allowed"
                        : "bg-indigo-600 hover:bg-indigo-500 text-white",
                    )}
                  >
                    {isSaving ? "Saving…" : "Save agent"}
                  </button>
                </div>
              )}
              {compiledConfig && agentId && (
                <div className="ml-auto flex items-center gap-2">
                  {dryRunBlocking && (
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={saveAnyway}
                        onChange={(e) => setSaveAnyway(e.target.checked)}
                        className="accent-indigo-500"
                      />
                      <span className="text-[10px] text-neutral-500">Save anyway</span>
                    </label>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={!isDirty || isSaving || dryRunBlocking}
                    className={cn(
                      "text-[10px] font-semibold px-3 py-1 rounded transition-colors",
                      !isDirty || isSaving || dryRunBlocking
                        ? "bg-white/[0.06] text-neutral-500 cursor-not-allowed"
                        : "bg-white/[0.06] hover:bg-white/[0.1] text-neutral-300 border border-white/[0.08]",
                    )}
                  >
                    {isSaving ? "Saving…" : "Save changes"}
                  </button>
                </div>
              )}
            </div>

            {/* Dry-run panel (only shown in form view with a config) */}
            {viewMode === "form" && compiledConfig && (
              <DryRunPanel
                config={compiledConfig}
                onResult={(r) => {
                  setDryRunResult(r)
                  // Reset "save anyway" whenever a new test result arrives
                  setSaveAnyway(false)
                }}
              />
            )}

            {/* Editor pane */}
            <div className="flex-1 overflow-hidden">
              {viewMode === "form" && compiledConfig ? (
                <AgentFormView
                  config={compiledConfig}
                  tools={tools}
                  skills={skills}
                  onChange={handleFormChange}
                  errors={validationErrors}
                />
              ) : (
                <YamlEditor
                  onCreateAgent={handleCreateAgent}
                  yamlError={yamlError}
                />
              )}
            </div>
          </>
        ) : (
          <TemplateBrowser onSelect={handleTemplateSelect} />
        )}

        {/* Start session row */}
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
