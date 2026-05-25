export type IndexProgressState = Record<string, unknown>

export function isIndexRunning(progress: IndexProgressState): boolean {
  return String(progress.status ?? '') === 'running'
}

export function indexPercent(progress: IndexProgressState): number {
  const status = String(progress.status ?? '')
  if (status === 'completed') return 100
  const total = Number(progress.total_files ?? 0)
  if (total <= 0) return status === 'running' ? 0 : 0
  const scanned = Number(progress.files_scanned ?? 0)
  if (status === 'running' && scanned > 0) {
    return Math.min(99, Math.round((scanned / total) * 100))
  }
  const done =
    Number(progress.files_indexed ?? 0) +
    Number(progress.files_skipped ?? 0) +
    Number(progress.files_failed ?? 0)
  return Math.min(100, Math.round((done / total) * 100))
}

export function formatProgressLine(progress: IndexProgressState): string {
  const total = Number(progress.total_files ?? 0)
  const scanned = Number(progress.files_scanned ?? 0)
  const indexed = Number(progress.files_indexed ?? 0)
  const skipped = Number(progress.files_skipped ?? 0)
  const failed = Number(progress.files_failed ?? 0)
  const current = progress.current_file ? String(progress.current_file) : '—'
  const status = String(progress.status ?? 'unknown')
  const pct = indexPercent(progress)

  if (status === 'completed') {
    return `Готово: ${indexed} проиндексировано, ${skipped} пропущено, ${failed} ошибок (${total} файлов)`
  }
  if (status === 'cancelled') return 'Индексация отменена'
  if (status === 'failed') return `Ошибка: ${progress.error ?? 'unknown'}`
  return `[${pct}%] ${scanned}/${total || '?'} — ${current} (indexed: ${indexed}, skipped: ${skipped})`
}
