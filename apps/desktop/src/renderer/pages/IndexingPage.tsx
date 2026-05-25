import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useAppStore } from '@/state/store'
import { ErrorBanner, formatIpcError, VaultGate } from '@/components/VaultGate'
import { Btn } from './ProjectPage'

export function IndexingPage() {
  const { project, setProject } = useAppStore()
  const [status, setStatus] = useState<Record<string, unknown>>({})
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = async () => {
    try {
      setError(null)
      const result = await api.getIndexStatus(project?.projectRoot)
      setStatus(result)
    } catch (e) {
      setError(formatIpcError(e))
    }
  }

  useEffect(() => {
    api.getCurrentProject().then(setProject).catch(() => {})
  }, [setProject])

  useEffect(() => {
    if (!project?.configured) return
    refresh()
    const id = setInterval(refresh, polling ? 2000 : 10000)
    return () => clearInterval(id)
  }, [polling, project?.configured, project?.projectRoot])

  const progress = (status.progress as Record<string, unknown>) ?? {}

  return (
    <VaultGate>
      <div className="space-y-4">
        <h1 className="text-lg font-semibold">Indexing</h1>
        {error && <ErrorBanner message={error} />}
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
        <div className="flex gap-2 flex-wrap">
          <Btn
            onClick={async () => {
              try {
                setPolling(true)
                setError(null)
                await api.startIndexing({ projectRoot: project?.projectRoot, mode: 'incremental' })
                await refresh()
              } catch (e) {
                setError(formatIpcError(e))
                setPolling(false)
              }
            }}
          >
            Build index
          </Btn>
          <Btn
            variant="secondary"
            onClick={async () => {
              try {
                setPolling(true)
                setError(null)
                await api.startIndexing({ projectRoot: project?.projectRoot, mode: 'full' })
                await refresh()
              } catch (e) {
                setError(formatIpcError(e))
                setPolling(false)
              }
            }}
          >
            Rebuild full index
          </Btn>
          <Btn
            variant="secondary"
            onClick={async () => {
              try {
                await api.cancelIndexing(String(progress.job_id ?? ''))
                setPolling(false)
                await refresh()
              } catch (e) {
                setError(formatIpcError(e))
              }
            }}
          >
            Cancel
          </Btn>
          <Btn variant="secondary" onClick={() => api.openAppDataFolder(project?.projectRoot)}>
            Open logs
          </Btn>
        </div>
      </div>
    </VaultGate>
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
