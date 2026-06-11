import { Notice } from "obsidian";
import type { LlmPullProgress } from "./llmConfig";

const MILESTONES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] as const;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => window.setTimeout(r, ms));
}

export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"] as const;
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v < 10 && i > 0 ? v.toFixed(1) : Math.round(v)} ${units[i]}`;
}

export function llmPullPercent(p: LlmPullProgress): number {
  if (p.percent > 0) return Math.min(100, p.percent);
  if (p.total > 0) return Math.min(100, Math.floor((p.completed / p.total) * 100));
  return 0;
}

function notifyMilestones(p: LlmPullProgress, notified: Set<number>): void {
  const pct = llmPullPercent(p);
  const model = p.model || "модель";
  for (const m of MILESTONES) {
    if (pct >= m && !notified.has(m)) {
      notified.add(m);
      const size =
        p.total > 0 ? ` (${formatBytes(p.completed)} / ${formatBytes(p.total)})` : "";
      new Notice(`Загрузка LLM ${model}: ${m}%${size}`);
    }
  }
}

export function renderLlmPullProgress(el: HTMLElement, p: LlmPullProgress): void {
  el.empty();
  if (!p.active && p.status !== "success" && !p.error) return;

  const pct = llmPullPercent(p);
  const model = p.model || "модель";

  if (p.error) {
    el.createEl("p", { text: `Ошибка загрузки ${model}: ${p.error}`, cls: "ocm-llm-error" });
    return;
  }

  if (!p.active && p.status === "success") {
    el.createEl("p", { text: `Модель ${model} загружена ✓`, cls: "ocm-llm-pull-done" });
    return;
  }

  const label = el.createEl("p", { cls: "ocm-llm-pull-label" });
  const size =
    p.total > 0 ? ` · ${formatBytes(p.completed)} / ${formatBytes(p.total)}` : "";
  label.setText(`Загрузка ${model}: ${pct}%${size}`);

  const track = el.createDiv({ cls: "ocm-llm-pull-track" });
  const fill = track.createDiv({ cls: "ocm-llm-pull-fill" });
  fill.style.width = `${pct}%`;
}

/** Poll LLM pull job; Obsidian notices every 10% + optional UI callback. */
export async function watchLlmPullProgress(
  poll: () => Promise<LlmPullProgress>,
  opts?: {
    onUpdate?: (p: LlmPullProgress) => void;
    timeoutMs?: number;
  }
): Promise<LlmPullProgress> {
  const timeoutMs = opts?.timeoutMs ?? 3_600_000;
  const notified = new Set<number>();
  const started = Date.now();
  let last: LlmPullProgress | null = null;

  while (Date.now() - started < timeoutMs) {
    const p = await poll();
    last = p;
    opts?.onUpdate?.(p);
    notifyMilestones(p, notified);

    if (!p.active) {
      if (p.error) {
        new Notice(`Загрузка LLM: ошибка — ${p.error}`);
      } else if (!notified.has(100)) {
        notified.add(100);
        new Notice(`Загрузка LLM ${p.model || ""}: 100% — готово`);
      }
      return p;
    }

    await sleep(500);
  }

  new Notice("Загрузка LLM: превышено время ожидания");
  return last ?? (await poll());
}
