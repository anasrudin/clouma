"use client"
import { cn } from "@/lib/utils"
import { useAgentStore } from "@/store/agent"

const STEPS = [
  { n: 1, label: "Create agent", sub: "POST /v1/agents" },
  { n: 2, label: "Configure environment", sub: null },
  { n: 3, label: "Start session", sub: null },
  { n: 4, label: "Integrate", sub: null },
]

export function StepBar() {
  const currentStep = useAgentStore((s) => s.currentStep)

  return (
    <div className="h-9 border-b border-white/[0.06] flex items-center px-4 gap-0 bg-[#0e0e10] overflow-x-auto shrink-0">
      <span className="text-[11px] text-neutral-500 pr-4 border-r border-white/[0.06] mr-4 shrink-0">
        Quickstart
      </span>
      {STEPS.map((step) => (
        <div key={step.n} className="flex items-center shrink-0">
          <div className="flex items-center gap-1.5 pr-4 border-r border-white/[0.06] mr-4 last:border-0">
            <div
              className={cn(
                "w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0",
                step.n <= currentStep
                  ? "bg-indigo-600 text-white"
                  : "border border-white/10 text-neutral-600"
              )}
            >
              {step.n}
            </div>
            <span
              className={cn(
                "text-[11px]",
                step.n === currentStep
                  ? "text-violet-300 font-semibold"
                  : step.n < currentStep
                  ? "text-neutral-400"
                  : "text-neutral-600"
              )}
            >
              {step.label}
            </span>
            {step.sub && step.n <= currentStep && (
              <span className="bg-white/[0.06] text-neutral-500 text-[9px] font-mono px-1.5 py-0.5 rounded">
                {step.sub}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
