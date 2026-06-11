import { App, EventRef, TFile } from "obsidian";
import type { SidecarClient } from "./sidecar/client";

/** Reindex only after this much idle time since the last vault change. */
export const AUTO_INDEX_IDLE_MS = 2 * 60 * 1000;

const SKIP_PREFIXES = [".obsidian/", ".trash/"];

function shouldIndex(path: string): boolean {
  const p = path.replace(/\\/g, "/");
  if (!p.toLowerCase().endsWith(".md")) return false;
  return !SKIP_PREFIXES.some((pre) => p.startsWith(pre));
}

/** Idle-based reindex: accumulate changes, flush after inactivity. */
export class VaultAutoIndexer {
  private changedPaths = new Set<string>();
  private idleTimer: number | null = null;
  private eventRefs: EventRef[] = [];

  constructor(
    private app: App,
    private getClient: () => SidecarClient | null,
    private idleMs: number = AUTO_INDEX_IDLE_MS
  ) {}

  attach(registerEvent: (ref: EventRef) => void): void {
    const markChanged = (path: string) => {
      if (!shouldIndex(path)) return;
      this.changedPaths.add(path);
      this.resetIdleTimer();
    };

    const track = (ref: EventRef) => {
      this.eventRefs.push(ref);
      registerEvent(ref);
    };

    track(
      this.app.vault.on("create", (file) => {
        if (file instanceof TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("modify", (file) => {
        if (file instanceof TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("delete", (file) => {
        if (file instanceof TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("rename", (file, oldPath) => {
        if (oldPath && shouldIndex(oldPath)) markChanged(oldPath);
        if (file instanceof TFile) markChanged(file.path);
      })
    );
  }

  detach(): void {
    this.clearIdleTimer();
    this.changedPaths.clear();
    this.eventRefs = [];
  }

  private resetIdleTimer(): void {
    this.clearIdleTimer();
    this.idleTimer = window.setTimeout(() => void this.flush(), this.idleMs);
  }

  private clearIdleTimer(): void {
    if (this.idleTimer !== null) {
      window.clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
  }

  private async flush(): Promise<void> {
    this.idleTimer = null;
    if (this.changedPaths.size === 0) return;

    const paths = [...this.changedPaths];
    this.changedPaths.clear();

    const client = this.getClient();
    if (!client) {
      for (const path of paths) this.changedPaths.add(path);
      this.resetIdleTimer();
      return;
    }

    const results = await Promise.allSettled(paths.map((path) => client.indexFile(path)));
    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.status === "rejected") {
        console.warn("[obsidian-context-mcp] auto-index failed:", paths[i], result.reason);
        this.changedPaths.add(paths[i]);
      }
    }

    if (this.changedPaths.size > 0) {
      this.resetIdleTimer();
    }
  }
}
