"use client"
import { cn } from "@/lib/utils"
import type { AgentConfig, ValidationDelta, ToolDescriptor } from "@/store/agent"

// ---------------------------------------------------------------------------
// MODEL_ALLOWLIST — must match apps/api/agent_runtime/validator.py
// ---------------------------------------------------------------------------
const MODEL_OPTIONS = [
  "gemini-flash-latest",
  "gpt-4o-mini",
  "qwen/qwen3-coder-480b-a35b-instruct",
] as const

// ---------------------------------------------------------------------------
// AgentFormView props
// ---------------------------------------------------------------------------

interface AgentFormViewProps {
  config: AgentConfig
  tools: ToolDescriptor[]
  onChange: (next: AgentConfig) => void
  errors?: ValidationDelta | null
}

// ---------------------------------------------------------------------------
// Shared label + wrapper
// ---------------------------------------------------------------------------

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] font-medium text-neutral-400 uppercase tracking-wide">
        {label}
      </label>
      {children}
    </div>
  )
}

const inputBase =
  "bg-white/[0.04] border rounded px-2.5 py-1.5 text-[11px] text-neutral-200 outline-none transition-colors placeholder:text-neutral-600"
const inputNormal = "border-white/[0.08] focus:border-indigo-500/60"
const inputError = "border-red-500/60 focus:border-red-500"

// ---------------------------------------------------------------------------
// AgentFormView
// ---------------------------------------------------------------------------

export function AgentFormView({
  config,
  tools,
  onChange,
  errors,
}: AgentFormViewProps) {
  // Ensure loadTools was called if needed — parent should pass tools already
  const selectedTools = config.tools ?? []

  const setField = <K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) => {
    onChange({ ...config, [key]: value })
  }

  const toggleTool = (toolName: string) => {
    const next = selectedTools.includes(toolName)
      ? selectedTools.filter((t) => t !== toolName)
      : [...selectedTools, toolName]
    setField("tools", next)
  }

  const nameHasError = errors?.missing_required?.includes("name") ?? false
  const namePattern = /^[a-z][a-z0-9_]*$/
  const nameFormatError =
    config.name && !namePattern.test(config.name)
      ? "Name must be lowercase, start with a letter, only letters/digits/underscores"
      : null
  const modelHasError = (errors?.invalid_model != null && errors.invalid_model !== "")
  const unknownTools = new Set(errors?.unknown_tools ?? [])

  // Orphan tools: selected in config but not present in the catalog
  const catalogNames = new Set(tools.map((t) => t.name))
  const orphanTools = (config.tools ?? []).filter((name) => !catalogNames.has(name))

  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto h-full">
      {/* Name */}
      <Field label="Name">
        <input
          value={config.name}
          onChange={(e) => setField("name", e.target.value)}
          placeholder="my-agent"
          pattern="^[a-z][a-z0-9_]*$"
          className={cn(
            inputBase,
            nameFormatError || (nameHasError && !config.name) ? inputError : inputNormal,
          )}
        />
        {nameFormatError ? (
          <p className="text-amber-400 text-[10px] mt-1">{nameFormatError}</p>
        ) : nameHasError ? (
          <p className="text-[10px] text-red-400">Name is required</p>
        ) : (
          <p className="text-[10px] text-neutral-600">
            Lowercase letters, numbers, underscores. Must start with a letter.
          </p>
        )}
      </Field>

      {/* Model */}
      <Field label="Model">
        <select
          value={config.model}
          onChange={(e) => setField("model", e.target.value)}
          className={cn(
            inputBase,
            "appearance-none cursor-pointer",
            modelHasError ? inputError : inputNormal,
          )}
        >
          {MODEL_OPTIONS.map((m) => (
            <option key={m} value={m} className="bg-[#111113]">
              {m}
            </option>
          ))}
          {/* If the current value isn't in the allowlist show it so user knows */}
          {config.model && !MODEL_OPTIONS.includes(config.model as (typeof MODEL_OPTIONS)[number]) && (
            <option value={config.model} className="bg-[#111113] text-red-400">
              {config.model} (invalid)
            </option>
          )}
        </select>
        {modelHasError && (
          <p className="text-[10px] text-red-400">
            Model &apos;{errors?.invalid_model}&apos; is not in the allowlist
          </p>
        )}
      </Field>

      {/* Description */}
      <Field label="Description (optional)">
        <input
          value={config.description ?? ""}
          onChange={(e) =>
            setField("description", e.target.value || undefined)
          }
          placeholder="Briefly describe what this agent does..."
          className={cn(inputBase, inputNormal)}
        />
      </Field>

      {/* Instruction */}
      <Field label="Instruction">
        <textarea
          value={config.instruction}
          onChange={(e) => setField("instruction", e.target.value)}
          placeholder="You are a helpful assistant..."
          rows={5}
          className={cn(
            inputBase,
            inputNormal,
            "min-h-32 resize-y font-mono leading-relaxed",
          )}
        />
      </Field>

      {/* Tools */}
      <Field label="Tools">
        {tools.length === 0 && orphanTools.length === 0 ? (
          <p className="text-[10px] text-neutral-600">
            No tools available — start the API server to load the tool catalog.
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {tools.map((tool) => {
              const checked = selectedTools.includes(tool.name)
              const isUnknown = unknownTools.has(tool.name)
              return (
                <label
                  key={tool.name}
                  className={cn(
                    "flex items-start gap-2.5 p-2 rounded border cursor-pointer transition-colors",
                    checked
                      ? isUnknown
                        ? "bg-red-500/10 border-red-500/40"
                        : "bg-indigo-500/10 border-indigo-500/30"
                      : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTool(tool.name)}
                    className="mt-0.5 accent-indigo-500 shrink-0"
                  />
                  <div className="min-w-0">
                    <p
                      className={cn(
                        "text-[10.5px] font-mono font-semibold truncate",
                        isUnknown ? "text-red-400" : "text-indigo-300",
                      )}
                    >
                      {tool.name}
                      {isUnknown && (
                        <span className="ml-1 text-red-400 font-normal">(unknown)</span>
                      )}
                    </p>
                    {tool.description && (
                      <p className="text-[10px] text-neutral-500 leading-relaxed mt-0.5 line-clamp-2">
                        {tool.description}
                      </p>
                    )}
                  </div>
                </label>
              )
            })}

            {/* Orphan tools: selected in config but not in catalog */}
            {orphanTools.map((name) => (
              <label
                key={name}
                className="flex items-center gap-2.5 p-2 rounded border cursor-pointer transition-colors bg-amber-500/10 border-amber-500/30"
              >
                <input
                  type="checkbox"
                  checked={true}
                  onChange={() => toggleTool(name)}
                  className="mt-0.5 accent-amber-500 shrink-0"
                />
                <span className="font-mono text-xs text-amber-300">{name}</span>
                <span className="text-amber-400/70 text-[10px] ml-auto">unknown</span>
              </label>
            ))}
          </div>
        )}
      </Field>
    </div>
  )
}
