"use client"
import { cn } from "@/lib/utils"
import type { AgentConfig, ValidationDelta, ToolDescriptor, SkillDescriptor } from "@/store/agent"

// ---------------------------------------------------------------------------
// MODEL_ALLOWLIST — must match apps/api/agent_runtime/validator.py
// ---------------------------------------------------------------------------
const MODEL_OPTIONS = [
  "qwen/qwen3-coder-480b-a35b-instruct",
  "qwen/qwen3-next-80b-a3b-instruct",
  "meta/llama-3.1-405b-instruct",
  "meta/llama-3.1-70b-instruct",
  "meta/llama-3.1-8b-instruct",
  "nvidia/llama-3.1-nemotron-70b-instruct",
  "claude-haiku-4-5",
  "gpt-4o-mini",
  "gemini-flash-latest",
] as const

// ---------------------------------------------------------------------------
// AgentFormView props
// ---------------------------------------------------------------------------

interface AgentFormViewProps {
  config: AgentConfig
  tools: ToolDescriptor[]
  skills: SkillDescriptor[]
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
  skills,
  onChange,
  errors,
}: AgentFormViewProps) {
  const selectedTools = config.tools ?? []
  const selectedSkills = (config.skills as string[] | undefined) ?? []

  const setField = <K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) => {
    onChange({ ...config, [key]: value })
  }

  const toggleTool = (toolName: string) => {
    const next = selectedTools.includes(toolName)
      ? selectedTools.filter((t) => t !== toolName)
      : [...selectedTools, toolName]
    setField("tools", next)
  }

  const toggleSkill = (skillName: string) => {
    const next = selectedSkills.includes(skillName)
      ? selectedSkills.filter((s) => s !== skillName)
      : [...selectedSkills, skillName]
    onChange({ ...config, skills: next })
  }

  // Sort: checked items first, then alphabetically within each group
  const sortedTools = [...tools].sort((a, b) => {
    const aChecked = selectedTools.includes(a.name)
    const bChecked = selectedTools.includes(b.name)
    if (aChecked !== bChecked) return aChecked ? -1 : 1
    return a.name.localeCompare(b.name)
  })

  const sortedSkills = [...skills].sort((a, b) => {
    const aChecked = selectedSkills.includes(a.name)
    const bChecked = selectedSkills.includes(b.name)
    if (aChecked !== bChecked) return aChecked ? -1 : 1
    return a.name.localeCompare(b.name)
  })

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
        <input
          list="model-options"
          value={config.model}
          onChange={(e) => setField("model", e.target.value)}
          placeholder="e.g. qwen/qwen3-coder-480b-a35b-instruct"
          className={cn(inputBase, modelHasError ? inputError : inputNormal)}
        />
        <datalist id="model-options">
          {MODEL_OPTIONS.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
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
        {sortedTools.length === 0 && orphanTools.length === 0 ? (
          <p className="text-[10px] text-neutral-600">
            No tools available — start the API server to load the tool catalog.
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {sortedTools.map((tool) => {
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

      {/* Skills */}
      <Field label="Skills">
        {sortedSkills.length === 0 ? (
          <p className="text-[10px] text-neutral-600">
            No skills available — start the API server to load the skill catalog.
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {sortedSkills.map((skill) => {
              const checked = selectedSkills.includes(skill.name)
              return (
                <label
                  key={skill.name}
                  className={cn(
                    "flex items-start gap-2.5 p-2 rounded border cursor-pointer transition-colors",
                    checked
                      ? "bg-violet-500/10 border-violet-500/30"
                      : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleSkill(skill.name)}
                    className="mt-0.5 accent-violet-500 shrink-0"
                  />
                  <div className="min-w-0">
                    <p className={cn(
                      "text-[10.5px] font-mono font-semibold truncate",
                      checked ? "text-violet-300" : "text-neutral-400",
                    )}>
                      {skill.name}
                    </p>
                    {skill.description && (
                      <p className="text-[10px] text-neutral-500 leading-relaxed mt-0.5 line-clamp-2">
                        {skill.description}
                      </p>
                    )}
                    {skill.tool_names.length > 0 && (
                      <p className="text-[9px] text-neutral-600 mt-0.5">
                        uses: {skill.tool_names.join(", ")}
                      </p>
                    )}
                  </div>
                </label>
              )
            })}
          </div>
        )}
      </Field>
    </div>
  )
}
