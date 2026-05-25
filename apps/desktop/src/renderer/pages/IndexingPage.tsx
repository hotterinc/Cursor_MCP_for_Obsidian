import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { formatProgressLine, indexPercent, isIndexRunning } from '@/lib/indexProgress'
import { useAppStore } from '@/state/store'
import { ErrorBanner, formatIpcError, VaultGate } from '@/components/VaultGate'
import { Spinner } from '@/components/Spinner'
import { Btn } from './ProjectPage'

const MAX_LOG_LINES = 300

function timestamp(): string {
  return new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function IndexingPage() {
  const { project, setProject } = useAppStore()
  const [status, setStatus] = useState<Record<string, unknown>>({})
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)

  const appendLog = useCallback((line: string) => {
    setLogs((prev) => [...prev.slice(-(MAX_LOG_LINES - 1)), line])
  }, [])

  const refresh = useCallback(async () => {
    try {
      setError(null)
      const result = await api.getIndexStatus(project?.projectRoot)
      setStatus(result)
      const progress = (result.progress as Record<string, unknown>) ?? {}
      if (isIndexRunning(progress)) setPolling(true)
      else if (polling && String(progress.status ?? '') !== 'running') setPolling(false)
    } catch (e) {
      setError(formatIpcError(e))
    }
  }, [polling, project?.projectRoot])

  useEffect(() => {
    api.getCurrentProject().then(setProject).catch(() => {})
  }, [setProject])

  useEffect(() => {
    if (!project?.configured) return
    refresh()
    const id = setInterval(refresh, polling ? 1500 : 10000)
    return () => clearInterval(id)
  }, [polling, project?.configured, project?.projectRoot, refresh])

  useEffect(() => {
    const unsubEvent = api.onSidecarEvent?.(({ method, params }) => {
      if (method === 'index.progress') {
        setStatus((prev) => ({ ...prev, progress: params, status: params.status ?? prev.status }))
        appendLog(`${timestamp()} ${formatProgressLine(params)}`)
        if (isIndexRunning(params)) setPolling(true)
        if (['completed', 'failed', 'cancelled'].includes(String(params.status ?? ''))) {
          setPolling(false)
        }
      }
    })
    const unsubLog = api.onSidecarLog?.((line) => {
      appendLog(`${timestamp()} ${line}`)
    })
    return () => {
      unsubEvent?.()
      unsubLog?.()
    }
  }, [appendLog])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const progress = (status.progress as Record<string, unknown>) ?? {}
  const running = isIndexRunning(progress) || polling
  const percent = indexPercent(progress)
  const total = Number(progress.total_files ?? 0)

  const startIndex = async (mode: 'incremental' | 'full') => {
    try {
      setPolling(true)
      setError(null)
      appendLog(`${timestamp()} Запуск индексации (${mode})…`)
      await api.startIndexing({ projectRoot: project?.projectRoot, mode })
      await refresh()
    } catch (e) {
      setError(formatIpcError(e))
      appendLog(`${timestamp()} Ошибка: ${formatIpcError(e)}`)
      setPolling(false)
    }
  }

  return (
    <VaultGate>
      <div className="flex flex-col gap-4 h-[calc(100vh-5.5rem)]">
        <div className="space-y-4 shrink-0">
          <h1 className="text-lg font-semibold">Indexing</h1>
          {error && <ErrorBanner message={error} />}

          {running && (
            <div className="flex items-center gap-2 rounded-md border border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))]/10 px-3 py-2 text-sm">
              <span className="text-[hsl(var(--primary))] font-medium">Идёт индексация…</span>
              <Spinner className="text-[hsl(var(--primary))]" />
              <span className="ml-auto font-mono text-[hsl(var(--primary))] tabular-nums">{percent}%</span>
            </div>
          )}

          <div className="grid gap-2 text-sm">
            <Row label="Status" value={String(status.status ?? progress.status ?? 'unknown')} />
            <Row label="Progress" value={total > 0 ? `${percent}% (${progress.files_scanned ?? 0}/${total})` : `${percent}%`} />
            <Row label="Files indexed" value={String(progress.files_indexed ?? 0)} />
            <Row label="Files skipped" value={String(progress.files_skipped ?? 0)} />
            <Row label="Files failed" value={String(progress.files_failed ?? 0)} />
            <Row label="Current file" value={String(progress.current_file ?? '—')} />
          </div>

          {(running || total > 0) && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Прогресс</span>
                <span className="font-mono tabular-nums">{percent}%</span>
              </div>
              <div className="w-full h-3 bg-[hsl(var(--accent))] rounded overflow-hidden">
                <div
                  className="h-full bg-[hsl(var(--primary))] transition-[width] duration-300 ease-out"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex gap-2 flex-wrap">
            <Btn onClick={() => startIndex('incremental')} disabled={running}>
              Build index
            </Btn>
            <Btn variant="secondary" onClick={() => startIndex('full')} disabled={running}>
              Rebuild full index
            </Btn>
            <Btn
              variant="secondary"
              disabled={!running}
              onClick={async () => {
                try {
                  await api.cancelIndexing(String(progress.job_id ?? ''))
                  appendLog(`${timestamp()} Отмена запрошена`)
                  setPolling(false)
                  await refresh()
                } catch (e) {
                  setError(formatIpcError(e))
                }
              }}
            >
              Cancel
            </Btn>
            <Btn variant="secondary" onClick={() => setLogs([])}>
              Clear log
            </Btn>
            <Btn variant="secondary" onClick={() => api.openAppDataFolder(project?.projectRoot)}>
              Open logs
            </Btn>
          </div>
        </div>

        <div className="flex-1 min-h-0 flex flex-col border border-[hsl(var(--border))] rounded-md overflow-hidden">
          <div className="px-3 py-2 text-xs font-medium text-slate-400 border-b border-[hsl(var(--border))] bg-[hsl(var(--muted))]">
            Лог индексации
          </div>
          <pre className="flex-1 overflow-auto p-3 text-xs font-mono text-slate-300 whitespace-pre-wrap break-all bg-[hsl(var(--background))]">
            {logs.length === 0 ? (
              <span className="text-slate-500">События индексации и Python backend появятся здесь…</span>
            ) : (
              logs.join('\n')
            )}
            <div ref={logEndRef} />
          </pre>
        </div>
      </div>
    </VaultGate>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-400 w-36 shrink-0">{label}</span>
      <span className="break-all">{value}</span>
    </div>
  )
}
