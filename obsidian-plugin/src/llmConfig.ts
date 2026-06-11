import type { PluginSettings } from "./types";

export const DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434";

export type LlmBackend = "local" | "ollama";

export interface LlmPreset {
  id: string;
  name: string;
  tier: "small" | "medium";
  sizeHint: string;
  description: string;
  backend?: LlmBackend;
}

export interface LlmPullProgress {
  active: boolean;
  model: string;
  status: string;
  completed: number;
  total: number;
  percent: number;
  error: string | null;
  backend?: LlmBackend;
}

export interface LlmStatus {
  health: { ok: boolean; host?: string; backend?: string; error?: string };
  installedModels: string[];
  modelAvailable: boolean;
  pull: LlmPullProgress;
  backend?: LlmBackend;
}

export interface LlmAskSource {
  relative_path: string;
  title: string;
  score: number;
  excerpt: string;
}

export interface LlmAskResult {
  answer: string;
  sources: LlmAskSource[];
}

export interface ActiveLlmConfig {
  backend: LlmBackend;
  host: string;
  model: string;
}

export function getActiveLlmConfig(settings: PluginSettings): ActiveLlmConfig | null {
  if (settings.llmMode === "off") return null;
  if (settings.llmMode === "preset") {
    if (!settings.llmPresetModel) return null;
    return { backend: "local", host: DEFAULT_OLLAMA_HOST, model: settings.llmPresetModel };
  }
  const host = settings.llmCustomHost?.trim() || DEFAULT_OLLAMA_HOST;
  const model = settings.llmCustomModel?.trim();
  if (!model) return null;
  return { backend: "ollama", host, model };
}

export function isLlmUiEnabled(settings: PluginSettings): boolean {
  return settings.llmMode !== "off" && Boolean(getActiveLlmConfig(settings));
}
