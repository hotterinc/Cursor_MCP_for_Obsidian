import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Btn } from './ProjectPage'

export function NotesPage() {
  const [notes, setNotes] = useState<Array<Record<string, unknown>>>([])
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null)
  const [preview, setPreview] = useState('')

  const load = async () => {
    const data = await api.listNotes({ query: filter || undefined })
    setNotes((data.notes as Array<Record<string, unknown>>) ?? [])
  }

  useEffect(() => {
    load()
  }, [])

  const read = async (rel: string) => {
    const note = await api.readNote({ relativePath: rel })
    setSelected(note)
    setPreview(String(note.content ?? '').slice(0, 2000))
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Notes</h1>
      <div className="flex gap-2">
        <input
          className="flex-1 px-2 py-1.5 rounded bg-[hsl(var(--accent))] border border-[hsl(var(--border))] text-sm"
          placeholder="Filter..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <Btn onClick={load}>Search</Btn>
      </div>
      <div className="grid grid-cols-2 gap-4 min-h-[400px]">
        <div className="border border-[hsl(var(--border))] rounded overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-[hsl(var(--muted))] sticky top-0">
              <tr>
                <th className="text-left p-2">Title</th>
                <th className="text-left p-2">Path</th>
              </tr>
            </thead>
            <tbody>
              {notes.map((n) => (
                <tr
                  key={String(n.relative_path)}
                  className="border-t border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))] cursor-pointer"
                  onClick={() => read(String(n.relative_path))}
                >
                  <td className="p-2">{String(n.title ?? n.relative_path)}</td>
                  <td className="p-2 text-xs text-slate-400">{String(n.relative_path)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border border-[hsl(var(--border))] rounded p-3 overflow-auto text-sm">
          {selected ? (
            <>
              <div className="font-medium mb-2">{String(selected.relative_path)}</div>
              <pre className="whitespace-pre-wrap text-xs text-slate-300">{preview}</pre>
              <Btn
                variant="secondary"
                onClick={() => api.openNoteInExternalApp({ relativePath: String(selected.relative_path) })}
              >
                Open externally
              </Btn>
            </>
          ) : (
            <span className="text-slate-500">Select a note</span>
          )}
        </div>
      </div>
    </div>
  )
}
