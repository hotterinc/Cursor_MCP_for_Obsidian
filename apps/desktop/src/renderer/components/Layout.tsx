import { useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { api } from '@/lib/api'
import { useAppStore } from '@/state/store'

const links = [
  { to: '/', label: 'Project' },
  { to: '/vault', label: 'Vault Setup' },
  { to: '/indexing', label: 'Indexing' },
  { to: '/search', label: 'Search' },
  { to: '/notes', label: 'Notes' },
  { to: '/settings', label: 'Settings' },
  { to: '/diagnostics', label: 'Diagnostics' }
]

export function Sidebar() {
  return (
    <aside className="w-48 border-r border-[hsl(var(--border))] bg-[hsl(var(--muted))] p-3 flex flex-col gap-1">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2 px-2">
        Obsidian Context
      </div>
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            cn(
              'px-2 py-1.5 rounded text-sm hover:bg-[hsl(var(--accent))]',
              isActive && 'bg-[hsl(var(--accent))] text-[hsl(var(--primary))]'
            )
          }
        >
          {l.label}
        </NavLink>
      ))}
    </aside>
  )
}

export function StatusBar() {
  const project = useAppStore((s) => s.project)
  const setProject = useAppStore((s) => s.setProject)

  useEffect(() => {
    api.getCurrentProject().then(setProject).catch(() => {
      /* sidecar may still be starting */
    })
  }, [setProject])

  return (
    <header className="h-10 border-b border-[hsl(var(--border))] flex items-center px-4 gap-4 text-xs">
      <span className="font-medium">{project?.projectName ?? 'No project'}</span>
      <span className="text-slate-400">{project?.projectRoot ?? '—'}</span>
      <span
        className={cn(
          'px-2 py-0.5 rounded',
          project?.configured ? 'bg-green-900/40 text-green-300' : 'bg-yellow-900/40 text-yellow-300'
        )}
      >
        {project?.status ?? 'not_configured'}
      </span>
    </header>
  )
}
