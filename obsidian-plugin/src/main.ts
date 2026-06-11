import { Notice, Plugin } from "obsidian";
import { SidecarClient } from "./sidecar/client";
import { SidecarManager } from "./sidecar/manager";
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
    await this.loadSettings();

    const dataDir = `${this.manifest.dir}/data`;
    const vaultPath = this.app.vault.adapter.basePath;
    if (!vaultPath) {
      new Notice("Obsidian Context MCP requires a local vault folder");
      return;
    }

    this.sidecar = new SidecarManager(vaultPath, dataDir, this.settings.pythonCommand);

    if (this.settings.autoStart) {
      await this.startSidecar();
    }

    this.addCommand({
      id: "ocm-semantic-search",
      name: "Semantic search vault",
      callback: () => this.openSearchModal(),
    });

    this.addCommand({
      id: "ocm-reindex",
      name: "Reindex vault for MCP",
      callback: () => this.reindexVault(),
    });

    this.addCommand({
      id: "ocm-scopes",
      name: "Manage Cursor access scopes",
      callback: () => this.openScopesModal(),
    });

    this.addStatusBarItem().setText("OCM").setTooltip(this.statusText).onClickEvent(() => {
      this.openSearchModal();
    });

    this.addSettingTab(new ObsidianContextSettingTab(this.app, this));
  }

  async onunload() {
    await this.sidecar?.stop();
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
    if (!this.sidecar) return;
    try {
      this.runtime = await this.sidecar.start();
      this.client = SidecarClient.fromRuntime(this.runtime);
      const status = await this.client.status();
      this.statusText = `Indexed ${status.fileCount} files (${status.indexStatus})`;
    } catch (e) {
      this.statusText = `Error: ${e}`;
      new Notice(`Failed to start vault-server: ${e}`);
    }
  }

  private ensureClient(): SidecarClient {
    if (!this.client) {
      throw new Error("vault-server is not running. Enable auto-start in settings or restart Obsidian.");
    }
    return this.client;
  }

  async openSearchModal() {
    if (!this.client) await this.startSidecar();
    new SearchModal(this.app, this.ensureClient()).open();
  }

  openScopesModal() {
    if (!this.client) {
      this.startSidecar().then(() => {
        new ScopesModal(this.app, this.ensureClient()).open();
      });
      return;
    }
    new ScopesModal(this.app, this.client).open();
  }

  async reindexVault() {
    if (!this.client) await this.startSidecar();
    await this.ensureClient().reindex("incremental");
    new Notice("Reindex started");
  }
}
