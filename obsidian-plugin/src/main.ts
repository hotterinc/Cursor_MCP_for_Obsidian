import { Notice, Plugin, setTooltip } from "obsidian";
import { SidecarClient } from "./sidecar/client";
import { SidecarManager } from "./sidecar/manager";
import { resolvePluginDataDir, resolvePluginDir } from "./paths";
import { ObsidianContextSettingTab } from "./settings";
import { DEFAULT_SETTINGS, PluginSettings, VaultRuntimeInfo } from "./types";
import { ScopesModal } from "./views/ScopesModal";
import { SearchModal } from "./views/SearchModal";

export default class ObsidianContextPlugin extends Plugin {
  settings: PluginSettings = DEFAULT_SETTINGS;
  private sidecar: SidecarManager | null = null;
  private client: SidecarClient | null = null;
  private runtime: VaultRuntimeInfo | null = null;
  statusText = "Not started";

  async onload() {
    try {
      await this.loadSettings();
      this.addSettingTab(new ObsidianContextSettingTab(this.app, this));

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
    try {
      await this.sidecar?.stop();
    } catch (e) {
      console.error("[obsidian-context-mcp] onunload:", e);
    }
    this.client = null;
    this.runtime = null;
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private async startSidecar() {
    try {
      const sidecar = this.ensureSidecar();
      this.runtime = await sidecar.start();
      this.client = SidecarClient.fromRuntime(this.runtime);
      const status = await this.client.status();
      this.statusText = `Indexed ${status.fileCount} files (${status.indexStatus})`;
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
      await this.ensureClient().reindex("incremental");
      const status = await this.client!.status();
      this.statusText = `Indexed ${status.fileCount} files (${status.indexStatus})`;
      new Notice("Reindex started");
    } catch (e) {
      new Notice(String(e));
      throw e;
    }
  }
}
