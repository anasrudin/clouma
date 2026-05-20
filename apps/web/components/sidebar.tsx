"use client"
import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard, Hammer, Bot, Settings, ChevronDown, ChevronRight, BookOpen, User
} from "lucide-react"

type NavItem = {
  label: string
  href?: string
  children?: { label: string; href: string }[]
}

const NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard" },
  {
    label: "Build",
    children: [
      { label: "Workbench", href: "/build/workbench" },
      { label: "Files", href: "/build/files" },
      { label: "Skills", href: "/build/skills" },
      { label: "Batches", href: "/build/batches" },
    ],
  },
  {
    label: "Managed Agents",
    children: [
      { label: "Quickstart", href: "/quickstart" },
      { label: "Agents", href: "/agents" },
      { label: "Sessions", href: "/sessions" },
      { label: "Environments", href: "/environments" },
      { label: "Credential vaults", href: "/credential-vaults" },
      { label: "Memory stores", href: "/memory-stores" },
    ],
  },
  {
    label: "Setting",
    children: [
      { label: "API keys", href: "/setting/api-keys" },
      { label: "Limits", href: "/setting/limits" },
      { label: "Service accounts", href: "/setting/service-accounts" },
      { label: "Security", href: "/setting/security" },
      { label: "Webhooks", href: "/setting/webhooks" },
    ],
  },
]

const ICONS: Record<string, React.ReactNode> = {
  Dashboard: <LayoutDashboard size={14} />,
  Build: <Hammer size={14} />,
  "Managed Agents": <Bot size={14} />,
  Setting: <Settings size={14} />,
}

function NavSection({ item }: { item: NavItem }) {
  const pathname = usePathname()
  const isActive = item.children?.some((c) => pathname.startsWith(c.href))
  const [open, setOpen] = useState(isActive ?? false)

  if (!item.children) {
    return (
      <Link
        href={item.href!}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded text-[11px] transition-colors",
          pathname === item.href
            ? "text-white bg-white/5"
            : "text-neutral-400 hover:text-white hover:bg-white/5"
        )}
      >
        {ICONS[item.label]}
        {item.label}
      </Link>
    )
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-1.5 rounded text-[11px] transition-colors",
          isActive ? "text-white" : "text-neutral-400 hover:text-white hover:bg-white/5"
        )}
      >
        {ICONS[item.label]}
        <span className="flex-1 text-left">{item.label}</span>
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <div className="ml-5 mt-0.5 flex flex-col gap-0.5">
          {item.children.map((child) => (
            <Link
              key={child.href}
              href={child.href}
              className={cn(
                "block px-3 py-1 rounded text-[10.5px] transition-colors",
                pathname === child.href
                  ? "text-violet-400 bg-violet-500/10 font-medium"
                  : "text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
              )}
            >
              {child.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export function Sidebar() {
  return (
    <aside className="w-[138px] flex-shrink-0 bg-[#111113] border-r border-white/[0.06] flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.06]">
        <div className="w-4 h-4 rounded bg-gradient-to-br from-indigo-500 to-violet-600 flex-shrink-0" />
        <span className="text-[11px] font-bold text-white leading-tight">Claude Console</span>
      </div>
      <div className="px-2 py-2 border-b border-white/[0.06]">
        <button className="w-full flex items-center justify-between bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1.5">
          <span className="text-[11px] text-neutral-300">Default</span>
          <ChevronDown size={10} className="text-neutral-500" />
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto py-2 flex flex-col gap-0.5 px-1">
        {NAV.map((item) => (
          <NavSection key={item.label} item={item} />
        ))}
      </nav>
      <div className="border-t border-white/[0.06] py-2 px-1">
        <button className="w-full flex items-center gap-2 px-3 py-1.5 text-[10.5px] text-neutral-500 hover:text-neutral-300 rounded hover:bg-white/5 transition-colors">
          <BookOpen size={12} />
          Documentation
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-1.5 text-[10.5px] text-neutral-500 rounded hover:bg-white/5 transition-colors justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center">
              <User size={10} className="text-neutral-400" />
            </div>
            <div className="text-left">
              <div className="text-[10px] text-neutral-300 font-medium">razor</div>
              <div className="text-[9px] text-neutral-600">Admin · org</div>
            </div>
          </div>
          <ChevronDown size={9} className="text-neutral-600" />
        </button>
      </div>
    </aside>
  )
}
