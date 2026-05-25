import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useAppStore } from '@/state/store'
import { Btn } from './ProjectPage'

export function VaultSetupPage() {
  const { project, setProject } = useAppStore()
  const [vaultPath, setVaultPath] = useState('')
  const [writeAccess, setWriteAccess] = useState(false)
  const [backup, setBackup] = useState(true)
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null)
  const [include, setInclude] = useState('**/*.md')
  const [exclude, setExclude] = useState('.obsidian/**, .git/**, node_modules/**')

  useEffect(() => {
    api.getCurrentProject().then((p) => {
      setProject(p)
      if (p.vaultPath) setVaultPath(p.vaultPath)
    })
    api.getSettings().then((s) => {
      setWriteAccess(Boolean(s.writeAccess))
      setBackup(Boolean(s.backupBeforeEdit))
      if (Array.isArray(s.include)) setInclude(s.include.join(', '))
      if (Array.isArray(s.exclude)) setExclude(s.exclude.join(', '))
    })
  }, [setProject])

  const revalidate = async () => {
    if (!vaultPath) return
    const result = await api.chooseVaultFolder(project?.projectRoot)
    if (result && !result.canceled) {
      setVaultPath(String(result.vaultPath))
      setValidation(result)
    }
  }

  const save = async () => {
    if (!project?.projectRoot || !vaultPath) return
    await api.saveProjectConfig({
      projectRoot: project.projectRoot,
      vaultPath,
      writeAccess,
      backupBeforeEdit: backup,
      include: include.split(',').map((s) => s.trim()),
      exclude: exclude.split(',').map((s) => s.trim())
    })
    setProject(await api.getCurrentProject())
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-lg font-semibold">Vault Setup</h1>
      <Field label="Vault path" value={vaultPath} onChange={setVaultPath} />
      {validation && (
        <div className="text-sm text-slate-400">
          {String(validation.markdownFilesCount)} markdown files
          {Array.isArray(validation.warnings) && validation.warnings.length > 0 && (
            <ul className="list-disc ml-4 mt-1">
              {(validation.warnings as string[]).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <Field label="Include patterns" value={include} onChange={setInclude} />
      <Field label="Exclude patterns" value={exclude} onChange={setExclude} />
      <Toggle label="Allow Cursor agents to edit documentation" checked={writeAccess} onChange={setWriteAccess} />
      <Toggle label="Create backup before every edit" checked={backup} onChange={setBackup} />
      <div className="flex gap-2">
        <Btn onClick={save}>Save configuration</Btn>
        <Btn variant="secondary" onClick={() => api.openVaultFolder()}>Open folder</Btn>
        <Btn variant="secondary" onClick={revalidate}>Revalidate</Btn>
      </div>
    </div>
  )
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block text-sm">
      <span className="text-slate-400">{label}</span>
      <input
        className="mt-1 w-full px-2 py-1.5 rounded bg-[hsl(var(--accent))] border border-[hsl(var(--border))]"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}

function Toggle({
  label,
  checked,
  onChange
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  )
}
