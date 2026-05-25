import { useState } from 'react'
import { api } from '@/lib/api'
import { Btn } from './ProjectPage'

export function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<'hybrid' | 'semantic' | 'lexical'>('hybrid')
  const [topK, setTopK] = useState(10)
  const [results, setResults] = useState<Array<Record<string, unknown>>>([])

  const search = async () => {
    const data = await api.searchDocs({ query, mode, topK })
    setResults((data.results as Array<Record<string, unknown>>) ?? [])
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Search</h1>
      <div className="flex gap-2 flex-wrap items-end">
        <label className="text-sm flex-1 min-w-[200px]">
          <span className="text-slate-400">Query</span>
          <input
            className="mt-1 w-full px-2 py-1.5 rounded bg-[hsl(var(--accent))] border border-[hsl(var(--border))]"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-400">Mode</span>
          <select
            className="mt-1 block px-2 py-1.5 rounded bg-[hsl(var(--accent))] border border-[hsl(var(--border))]"
            value={mode}
            onChange={(e) => setMode(e.target.value as typeof mode)}
          >
            <option value="hybrid">hybrid</option>
            <option value="semantic">semantic</option>
            <option value="lexical">lexical</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="text-slate-400">topK</span>
          <input
            type="number"
            className="mt-1 w-20 px-2 py-1.5 rounded bg-[hsl(var(--accent))] border border-[hsl(var(--border))]"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </label>
        <Btn onClick={search}>Search</Btn>
      </div>
      <div className="space-y-3">
        {results.map((r) => (
          <div key={String(r.chunk_id)} className="border border-[hsl(var(--border))] rounded p-3 text-sm">
            <div className="font-medium">{String(r.title)}</div>
            <div className="text-slate-400 text-xs">{String(r.relative_path)} · score {Number(r.score).toFixed(3)}</div>
            <div className="text-xs text-slate-500 mt-1">
              L{String(r.start_line)}–{String(r.end_line)}
              {Array.isArray(r.heading_path) && r.heading_path.length > 0 && ` · ${(r.heading_path as string[]).join(' > ')}`}
            </div>
            <p className="mt-2 text-slate-300 line-clamp-3">{String(r.text)}</p>
            <div className="mt-2 flex gap-2">
              <Btn
                variant="secondary"
                onClick={() => api.openNoteInExternalApp({ relativePath: String(r.relative_path) })}
              >
                Open note
              </Btn>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
