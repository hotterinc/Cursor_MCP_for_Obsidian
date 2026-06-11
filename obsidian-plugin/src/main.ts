import { Notice, Plugin, setTooltip } from "obsidian";
import { SidecarClient } from "./sidecar/client";
import { SidecarManager } from "./sidecar/manager";
import { resolvePluginDataDir, resolvePluginDir } from "./paths";
import { watchReindexProgress, formatIndexStatus } from "./reindexProgress";
import { ObsidianContextSettingTab } from "./settings";
import { DEFAULT_SETTINGS, PluginSettings, VaultRuntimeInfo } from "./types";
import { ScopesModal } from "./views/ScopesModal";
import { SearchModal } from "./views/SearchModal";

export default class ObsidianContextPlugin extends Plugin {
  settings: PluginSettings = DEFAULT_SETTINGS;
  private sidecar: SidecarManager | null = null;
  private client: SidecarClient | null = null;
  private runtime: VaultRuntimeInfo | null = null;
  private startPromise: Promise<void> | null = null;
  private settingTab: ObsidianContextSettingTab | null = null;
  statusText = "Not started";

  async onload() {
    try {
      await this.loadSettings();
      this.settingTab = new ObsidianContextSettingTab(this.app, this);
      this.addSettingTab(this.settingTab);

      const pluginDir = resolvePluginDir(this.app, this.manifest);
      const dataDir = resolvePluginDataDir(this.app, this.manifest);
      const vaultPath = this.getVaultPath();
      if (!vaultPath) {
        this.statusText = "Нужен локальный vault (не облачный без basePath)";
        new Notice("Obsidian Context MCP: открой локальный vault или укажи Python command в настройках.");
        return;
      }

      this.sidecar = new SidecarManager(
        vaultPath,
        pluginDir,
        dataDir,
        this.settings.pythonCommand
      );

      this.addCommand({
        id: "ocm-semantic-search",
        name: "Semantic search vault",
        callback: () => void this.openSearchModal(),
      });

      this.addCommand({
        id: "ocm-reindex",
        name: "Reindex vault for MCP",
        callback: () => void this.reindexVault(),
      });

      this.addCommand({
        id: "ocm-scopes",
        name: "Manage Cursor access scopes",
        callback: () => void this.openScopesModal(),
      });

      this.addCommand({
        id: "ocm-restart-server",
        name: "Restart vault-server",
        callback: () => void this.restartSidecarIfNeeded(),
      });

      this.addRibbonIcon("scan-search", "Семантический поиск vault", () => {
        void this.openSearchModal();
      });

      const statusItem = this.addStatusBarItem();
      statusItem.setText("OCM");
      setTooltip(statusItem, this.statusText);
      statusItem.onClickEvent(() => void this.openSearchModal());

      // Defer sidecar start so Obsidian finishes plugin init first.
      if (this.settings.autoStart) {
        window.setTimeout(() => {
          void this.startSidecar().catch((e) => new Notice(String(e)));
        }, 500);
      }
    } catch (e) {
      console.error("[obsidian-context-mcp] onload failed:", e);
      this.statusText = `Plugin error: ${e}`;
      new Notice(`Obsidian Context MCP: ошибка загрузки — ${e}`);
    }
  }

  refreshSettingsDisplay(): void {
    this.settingTab?.display();
  }

  private applyVaultStatus(status: { fileCount: number; vaultFileCount?: number; indexStatus: string }): void {
    this.statusText = formatIndexStatus(
      status.fileCount,
      status.vaultFileCount ?? status.fileCount,
      status.indexStatus
    );
    this.refreshSettingsDisplay();
  }

  private getVaultPath(): string | null {
    const adapter = this.app.vault.adapter as { basePath?: string };
    return adapter.basePath ?? null;
  }

  private ensureSidecar(): SidecarManager {
    if (this.sidecar) return this.sidecar;
    const vaultPath = this.getVaultPath();
    if (!vaultPath) {
      throw new Error("Нужен локальный vault (не облачный без basePath)");
    }
    const pluginDir = resolvePluginDir(this.app, this.manifest);
    const dataDir = resolvePluginDataDir(this.app, this.manifest);
    this.sidecar = new SidecarManager(
      vaultPath,
      pluginDir,
      dataDir,
      this.settings.pythonCommand
    );
    return this.sidecar;
  }

  async restartSidecarIfNeeded(): Promise<void> {
    const vaultPath = this.getVaultPath();
    if (!vaultPath) {
      throw new Error("Нужен локальный vault");
    }
    const sidecar = this.ensureSidecar();
    await sidecar.forceStopForRestart();
    this.client = null;
    this.runtime = null;
    await this.startSidecar();
    new Notice("vault-server перезапущен");
  }

  async onunload() {
    if (this.settings.stopServerOnQuit) {
      try {
        await this.sidecar?.forceStopForRestart();
      } catch (e) {
        console.error("[obsidian-context-mcp] stop on quit:", e);
      }
    }
    this.client = null;
    this.runtime = null;
    this.startPromise = null;
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private async startSidecar(): Promise<void> {
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.startSidecarOnce().finally(() => {
      this.startPromise = null;
    });
    return this.startPromise;
  }

  private async startSidecarOnce() {
    try {
      const sidecar = this.ensureSidecar();
      this.runtime = await sidecar.start();
      this.client = SidecarClient.fromRuntime(this.runtime);
      const status = await this.client.status();
      this.applyVaultStatus(status);
    } catch (e) {
      console.error("[obsidian-context-mcp] startSidecar:", e);
      this.statusText = `Error: ${e}`;
      this.client = null;
      this.runtime = null;
      throw e;
    }
  }

  private ensureClient(): SidecarClient {
    if (!this.client) {
      throw new Error("vault-server is not running. Command palette → Restart vault-server");
    }
    return this.client;
  }

  async openSearchModal() {
    try {
      if (!this.client) await this.startSidecar();
      new SearchModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new Notice(String(e));
      throw e;
    }
  }

  async openScopesModal() {
    try {
      if (!this.client) await this.startSidecar();
      new ScopesModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new Notice(String(e));
      throw e;
    }
  }

  async reindexVault() {
    try {
      if (!this.client) await this.startSidecar();
      const client = this.ensureClient();
      await client.reindex("incremental");
      await watchReindexProgress(() => client.indexJobStatus());
      const status = await client.status();
      this.applyVaultStatus(status);
    } catch (e) {
      new Notice(String(e));
      throw e;
    }
  }
}
