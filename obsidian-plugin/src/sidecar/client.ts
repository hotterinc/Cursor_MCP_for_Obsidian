import type { AccessScope, SearchResult, VaultRuntimeInfo } from "../types";

export class SidecarClient {
  constructor(private baseUrl: string) {}

  static fromRuntime(runtime: VaultRuntimeInfo): SidecarClient {
    return new SidecarClient(`http://${runtime.host}:${runtime.port}`);
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    return (await res.json()) as T;
  }

  health() {
    return this.request<{ ok: boolean }>("/health");
  }

  status() {
    return this.request<{ fileCount: number; indexStatus: string; job: unknown }>("/api/v1/status");
  }

  search(query: string, topK = 10) {
    return this.request<{ results: SearchResult[] }>("/api/v1/search", {
      method: "POST",
      body: JSON.stringify({ query, topK, mode: "hybrid" }),
    });
  }

  reindex(mode: "full" | "incremental" = "incremental") {
    return this.request<unknown>("/api/v1/reindex", {
      method: "POST",
      body: JSON.stringify({ mode }),
    });
  }

  listScopes() {
    return this.request<{ scopes: AccessScope[] }>("/api/v1/scopes");
  }

  upsertScope(scope: AccessScope) {
    return this.request<AccessScope>("/api/v1/scopes", {
      method: "POST",
      body: JSON.stringify(scope),
    });
  }

  deleteScope(scopeId: string) {
    return this.request<{ ok: boolean }>(`/api/v1/scopes/${encodeURIComponent(scopeId)}`, {
      method: "DELETE",
    });
  }

  regenerateToken(scopeId: string) {
    return this.request<AccessScope>(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}/regenerate-token`,
      { method: "POST" }
    );
  }

  cursorConfig(scopeId: string) {
    return this.request<{ config: unknown; scope: AccessScope }>(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}/cursor-config`
    );
  }

  scopePreview(scope: Partial<AccessScope>) {
    return this.request<{ fileCount: number; sample: string[] }>("/api/v1/scopes/preview", {
      method: "POST",
      body: JSON.stringify(scope),
    });
  }
}
