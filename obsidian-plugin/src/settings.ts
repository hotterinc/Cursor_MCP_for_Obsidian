import { App, PluginSettingTab, Setting } from "obsidian";
import type ObsidianContextPlugin from "./main";
import { DEFAULT_SETTINGS } from "./types";

export class ObsidianContextSettingTab extends PluginSettingTab {
  constructor(app: App, private plugin: ObsidianContextPlugin) {
    super(app, plugin);
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Obsidian Context MCP" });

    new Setting(containerEl)
      .setName("Python command")
      .setDesc("Command to run vault-server (default: obsidian-context-mcp in PATH, or bundled bin/)")
      .addText((text) =>
        text
          .setPlaceholder("obsidian-context-mcp")
          .setValue(this.plugin.settings.pythonCommand)
          .onChange(async (v) => {
            this.plugin.settings.pythonCommand = v || DEFAULT_SETTINGS.pythonCommand;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Auto-start sidecar")
      .setDesc("Start vault-server when Obsidian loads the vault")
      .addToggle((t) =>
        t.setValue(this.plugin.settings.autoStart).onChange(async (v) => {
          this.plugin.settings.autoStart = v;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Index status")
      .setDesc(this.plugin.statusText)
      .addButton((btn) =>
        btn.setButtonText("Reindex").onClick(async () => {
          await this.plugin.reindexVault();
          this.display();
        })
      );

    new Setting(containerEl)
      .setName("Access scopes")
      .setDesc("Manage Cursor access to specific vault folders")
      .addButton((btn) =>
        btn.setButtonText("Open scopes").onClick(() => {
          this.plugin.openScopesModal();
        })
      );
  }
}
