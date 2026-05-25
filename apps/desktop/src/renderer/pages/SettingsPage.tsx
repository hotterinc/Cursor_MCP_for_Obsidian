import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Btn } from './ProjectPage'

export function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, unknown>>({})

  useEffect(() => {
    api.getSettings().then(setSettings)
  }, [])

  const update = async (patch: Record<string, unknown>) => {
    await api.updateSettings(patch)
    setSettings(await api.getSettings())
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-lg font-semibold">Settings</h1>
      <div className="grid gap-2 text-sm">
        <Row label="Project root" value={String(settings.projectRoot ?? '—')} />
        <Row label="Vault path" value={String(settings.vaultPath ?? '—')} />
        <Row label="App data" value={String(settings.appDataPath ?? '—')} />
        <Row label="Embedding" value={`${settings.embeddingProvider} / ${settings.embeddingModel}`} />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={Boolean(settings.watcherEnabled)}
          onChange={(e) => update({ watcherEnabled: e.target.checked })}
        />
        Watcher enabled
      </label>
      <div className="flex gap-2 flex-wrap">
        <Btn variant="secondary" onClick={() => api.openAppDataFolder()}>Open app data</Btn>
        <Btn
          variant="secondary"
          onClick={async () => {
            await api.startIndexing({ mode: 'full' })
          }}
        >
          Reset index (full rebuild)
        </Btn>
      </div>
      <p className="text-xs text-slate-500">
        First use of sentence-transformers will download the embedding model locally. No document content is sent externally.
      </p>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-400 w-32">{label}</span>
      <span className="break-all">{value}</span>
    </div>
  )
}
