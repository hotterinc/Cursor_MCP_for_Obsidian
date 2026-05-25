import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { useAppStore } from '@/state/store'

export function ProjectPage() {
  const { project, setProject } = useAppStore()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.getCurrentProject().then(setProject).catch(console.error)
  }, [setProject])

  const chooseProject = async () => {
    setLoading(true)
    try {
      const result = await api.chooseProjectRoot()
      if (!('canceled' in result && result.canceled)) setProject(result)
    } finally {
      setLoading(false)
    }
  }

  const chooseVault = async () => {
    setLoading(true)
    try {
      const result = await api.chooseVaultFolder(project?.projectRoot)
      if (result && !result.canceled && project?.projectRoot) {
        await api.saveProjectConfig({
          projectRoot: project.projectRoot,
          vaultPath: result.vaultPath
        })
        const updated = await api.getCurrentProject()
        setProject(updated)
      }
    } catch (e) {
      alert(String(e instanceof Error ? e.message : e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Project</h1>
      <div className="grid gap-2 text-sm">
        <Row label="Project root" value={project?.projectRoot} />
        <Row label="Real path" value={project?.projectRealPath} />
        <Row label="Project name" value={project?.projectName} />
        <Row label="Project ID" value={project?.projectId} mono />
        <Row label="Vault path" value={project?.vaultPath} />
        <Row label="Configured" value={project?.configured ? 'Yes' : 'No'} />
      </div>
      <div className="flex gap-2 flex-wrap">
        <Btn onClick={chooseProject} disabled={loading}>Choose project root</Btn>
        <Btn onClick={chooseVault} disabled={loading || !project?.projectRoot}>Choose Obsidian folder</Btn>
        <Link to="/vault" className="btn-link"><Btn>Open vault setup</Btn></Link>
        <Link to="/diagnostics" className="btn-link"><Btn variant="secondary">Run diagnostics</Btn></Link>
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value?: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-400 w-32 shrink-0">{label}</span>
      <span className={mono ? 'font-mono text-xs break-all' : 'break-all'}>{value ?? '—'}</span>
    </div>
  )
}

function Btn({
  children,
  onClick,
  disabled,
  variant = 'primary'
}: {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={
        variant === 'primary'
          ? 'px-3 py-1.5 rounded bg-[hsl(var(--primary))] text-white text-sm disabled:opacity-50'
          : 'px-3 py-1.5 rounded border border-[hsl(var(--border))] text-sm disabled:opacity-50'
      }
    >
      {children}
    </button>
  )
}

export { Btn }
