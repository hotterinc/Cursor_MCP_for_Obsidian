import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Btn } from './ProjectPage'

export function DiagnosticsPage() {
  const [checks, setChecks] = useState<Array<Record<string, unknown>>>([])

  const run = async () => {
    const result = await api.runDiagnostics()
    setChecks((result.checks as Array<Record<string, unknown>>) ?? [])
  }

  useEffect(() => {
    run()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Diagnostics</h1>
        <Btn onClick={run}>Run again</Btn>
      </div>
      <div className="border border-[hsl(var(--border))] rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[hsl(var(--muted))]">
            <tr>
              <th className="text-left p-2">Check</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Message</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((c) => (
              <tr key={String(c.name)} className="border-t border-[hsl(var(--border))]">
                <td className="p-2 font-mono text-xs">{String(c.name)}</td>
                <td className="p-2">
                  <StatusBadge status={String(c.status)} />
                </td>
                <td className="p-2 text-slate-400">{String(c.message)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pass: 'text-green-400',
    warn: 'text-yellow-400',
    fail: 'text-red-400',
    skip: 'text-slate-500'
  }
  return <span className={colors[status] ?? 'text-slate-400'}>{status}</span>
}
