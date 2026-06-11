import { Notice } from "obsidian";
import type { IndexProgress } from "./types";

const MILESTONES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] as const;

function progressPercent(job: IndexProgress): number {
  if (!job.total_files) return 0;
  return Math.min(100, Math.floor((job.files_scanned / job.total_files) * 100));
}

function notifyMilestones(job: IndexProgress, notified: Set<number>): void {
  const pct = progressPercent(job);
  const total = job.total_files;
  const scanned = job.files_scanned;

  for (const m of MILESTONES) {
    if (pct >= m && !notified.has(m)) {
      notified.add(m);
      const detail = total > 0 ? ` (обработано ${scanned}/${total})` : "";
      new Notice(`Индексация: ${m}%${detail}`);
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Poll index job and show Obsidian notices at every 10% milestone. */
export async function watchReindexProgress(
  poll: () => Promise<IndexProgress | null>,
  timeoutMs = 3_600_000
): Promise<IndexProgress | null> {
  const notified = new Set<number>();
  const started = Date.now();

  new Notice("Индексация: старт…");

  while (Date.now() - started < timeoutMs) {
    const job = await poll();
    if (!job) {
      await sleep(400);
      continue;
    }

    notifyMilestones(job, notified);

    if (job.status === "completed") {
      if (!notified.has(100)) {
        notified.add(100);
        new Notice(
          `Индексация: 100% — обработано ${job.files_scanned}/${job.total_files}` +
            ` (${job.files_indexed} новых, ${job.files_skipped} без изменений` +
            `${job.files_failed ? `, ${job.files_failed} ошибок` : ""})`
        );
      }
      return job;
    }

    if (job.status === "failed" || job.status === "cancelled") {
      new Notice(
        `Индексация остановлена: ${job.status}${job.error ? ` — ${job.error}` : ""}`
      );
      return job;
    }

    await sleep(400);
  }

  new Notice("Индексация: превышено время ожидания");
  return null;
}

export function formatIndexStatus(
  indexed: number,
  total: number,
  indexStatus: string
): string {
  if (total > indexed) {
    return `Indexed ${indexed}/${total} files (${indexStatus})`;
  }
  return `Indexed ${indexed} files (${indexStatus})`;
}
