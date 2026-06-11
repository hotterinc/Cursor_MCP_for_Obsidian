import { requestUrl } from "obsidian";
import type {
  LlmAskResult,
  LlmPreset,
  LlmPullProgress,
  LlmStatus,
} from "../llmConfig";
import type { AccessScope, IndexProgress, SearchResult, VaultRuntimeInfo, VaultStatus } from "../types";

export class SidecarClient {
  constructor(private baseUrl: string) {}

  static fromRuntime(runtime: VaultRuntimeInfo): SidecarClient {
    return new SidecarClient(`http://${runtime.host}:${runtime.port}`);
  }

  private async request<T>(
    path: string,
    init?: { method?: string; body?: string }
  ): Promise<T> {
    const res = await requestUrl({
      url: `${this.baseUrl}${path}`,
      method: init?.method ?? "GET",
      headers: { "Content-Type": "application/json" },
      body: init?.body,
      throw: false,
    });
    if (res.status >= 400) {
      throw new Error(`${res.status}: ${res.text}`);
    }
    return res.json as T;
  }

  health() {
    return this.request<{ ok: boolean }>("/health");
  }

  status() {
    return this.request<VaultStatus>("/api/v1/status");
  }

  indexJobStatus() {
    return this.status().then((s) => s.job);
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

  indexFile(relativePath: string) {
    return this.request<{ ok: boolean; relativePath: string }>("/api/v1/index-file", {
      method: "POST",
      body: JSON.stringify({ relativePath }),
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
    return this.request<{ ok: boolean }>(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}`,
      { method: "DELETE" }
    );
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

  llmPresets() {
    return this.request<{ presets: LlmPreset[]; defaultHost: string }>("/api/v1/llm/presets");
  }

  llmStatus(host: string, model: string, backend: "local" | "ollama" = "local") {
    const q = new URLSearchParams({ host, model, backend });
    return this.request<LlmStatus>(`/api/v1/llm/status?${q}`);
  }

  llmPull(host: string, model: string, backend: "local" | "ollama" = "local") {
    return this.request<LlmPullProgress>("/api/v1/llm/pull", {
      method: "POST",
      body: JSON.stringify({ host, model, backend }),
    });
  }

  llmPullStatus() {
    return this.request<LlmPullProgress>("/api/v1/llm/pull-status");
  }

  llmAsk(query: string, host: string, model: string, backend: "local" | "ollama" = "local", topK = 8) {
    return this.request<LlmAskResult>("/api/v1/llm/ask", {
      method: "POST",
      body: JSON.stringify({ query, host, model, backend, topK }),
    });
  }
}
