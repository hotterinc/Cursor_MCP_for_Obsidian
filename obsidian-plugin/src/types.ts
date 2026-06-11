export interface VaultRuntimeInfo {
  port: number;
  pid: number;
  host: string;
  status: string;
  startedAt: string;
  vault_id: string;
}

export interface AccessScope {
  id: string;
  name: string;
  include: string[];
  exclude: string[];
  writeAccess: boolean;
  canReindex: boolean;
  token: string;
  tokenPreview?: string;
}

export interface SearchResult {
  chunk_id: string;
  relative_path: string;
  title: string;
  heading_path: string[];
  start_line: number;
  end_line: number;
  score: number;
  text: string;
}

export interface PluginSettings {
  pythonCommand: string;
  sidecarArgs: string;
  autoStart: boolean;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  pythonCommand: "obsidian-context-mcp",
  sidecarArgs: "",
  autoStart: true,
};
