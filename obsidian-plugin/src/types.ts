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
  writeInclude?: string[];
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

export interface IndexProgress {
  job_id: string;
  status: string;
  total_files: number;
  files_scanned: number;
  files_indexed: number;
  files_skipped: number;
  files_failed: number;
  chunks_created: number;
  chunks_embedded: number;
  current_file: string | null;
  queue_size: number;
  error: string | null;
}

export interface VaultStatus {
  fileCount: number;
  vaultFileCount: number;
  indexStatus: string;
  job: IndexProgress | null;
}

export interface PluginSettings {
  pythonCommand: string;
  sidecarArgs: string;
  autoStart: boolean;
  /** MCP HTTP port. 0 = random free port (not recommended for Cursor). */
  serverPort: number;
  /** Reindex changed .md notes automatically via vault events. */
  autoReindexOnChange: boolean;
  /** Stop vault-server when Obsidian exits (plugin onunload). */
  stopServerOnQuit: boolean;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  pythonCommand: "obsidian-context-mcp",
  sidecarArgs: "",
  autoStart: true,
  serverPort: 18432,
  autoReindexOnChange: true,
  stopServerOnQuit: false,
};
