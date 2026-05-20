import { Sidebar } from "@/components/sidebar"
import { StepBar } from "@/components/step-bar"

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-[#0e0e10] text-neutral-200 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <StepBar />
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  )
}
