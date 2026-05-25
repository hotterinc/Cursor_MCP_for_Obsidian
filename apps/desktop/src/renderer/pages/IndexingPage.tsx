import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Btn } from './ProjectPage'

export function IndexingPage() {
  const [status, setStatus] = useState<Record<string, unknown>>({})
  const [polling, setPolling] = useState(false)

  const refresh = async () => {
    const result = await api.getIndexStatus()
    setStatus(result)
  }

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, polling ? 2000 : 10000)
    return () => clearInterval(id)
  }, [polling])

  const progress = (status.progress as Record<string, unknown>) ?? {}

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Indexing</h1>
      <div className="grid gap-2 text-sm">
        <Row label="Status" value={String(status.status ?? 'unknown')} />
        <Row label="Files scanned" value={String(progress.files_scanned ?? 0)} />
        <Row label="Files indexed" value={String(progress.files_indexed ?? 0)} />
        <Row label="Files skipped" value={String(progress.files_skipped ?? 0)} />
        <Row label="Files failed" value={String(progress.files_failed ?? 0)} />
        <Row label="Current file" value={String(progress.current_file ?? '—')} />
      </div>
      {progress.files_scanned ? (
        <div className="w-full h-2 bg-[hsl(var(--accent))] rounded overflow-hidden">
          <div
            className="h-full bg-[hsl(var(--primary))]"
            style={{
              width: `${Math.min(100, ((Number(progress.files_indexed) || 0) / Number(progress.files_scanned)) * 100)}%`
            }}
          />
        </div>
      ) : null}
      <div className="flex gap-2">
        <Btn
          onClick={async () => {
            setPolling(true)
            await api.startIndexing({ mode: 'incremental' })
            await refresh()
          }}
        >
          Build index
        </Btn>
        <Btn
          variant="secondary"
          onClick={async () => {
            setPolling(true)
            await api.startIndexing({ mode: 'full' })
            await refresh()
          }}
        >
          Rebuild full index
        </Btn>
        <Btn
          variant="secondary"
          onClick={async () => {
            await api.cancelIndexing(String(progress.job_id ?? ''))
            setPolling(false)
            await refresh()
          }}
        >
          Cancel
        </Btn>
        <Btn variant="secondary" onClick={() => api.openAppDataFolder()}>
          Open logs
        </Btn>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-400 w-36">{label}</span>
      <span>{value}</span>
    </div>
  )
}
