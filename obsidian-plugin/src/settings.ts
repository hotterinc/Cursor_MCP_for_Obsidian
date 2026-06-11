import {
  activeSidecarPath,
  hasBundledSidecar,
  resolvePluginDir,
} from "./paths";
import { App, Notice, PluginSettingTab, Setting } from "obsidian";
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

    const pluginDir = resolvePluginDir(this.app, this.plugin.manifest);
    const bundled = hasBundledSidecar(pluginDir);
    const serverPath = activeSidecarPath(pluginDir, this.plugin.settings.pythonCommand);

    new Setting(containerEl)
      .setName("Program folder")
      .setDesc(pluginDir);

    new Setting(containerEl)
      .setName("Vault server")
      .setDesc(
        bundled
          ? `Встроен в плагин: ${serverPath}`
          : "Сервер не найден в plugin/. Запустите scripts/install-obsidian-plugin.sh"
      );

    if (!bundled) {
      new Setting(containerEl)
        .setName("Python command (dev fallback)")
        .setDesc("Только для разработки, если server/.venv не установлен")
        .addText((text) =>
          text
            .setPlaceholder("obsidian-context-mcp")
            .setValue(this.plugin.settings.pythonCommand)
            .onChange(async (v) => {
              this.plugin.settings.pythonCommand = v.trim() || DEFAULT_SETTINGS.pythonCommand;
              await this.plugin.saveSettings();
            })
        );
    }

    new Setting(containerEl)
      .setName("MCP server port")
      .setDesc(
        "Фиксированный порт для Cursor MCP (по умолчанию 18432). 0 = случайный порт при каждом запуске — тогда после рестарта нужно обновлять .cursor/mcp.json. После смены порта нажмите Restart server."
      )
      .addText((text) =>
        text
          .setPlaceholder("18432")
          .setValue(String(this.plugin.settings.serverPort))
          .onChange(async (v) => {
            const n = Number.parseInt(v.trim(), 10);
            this.plugin.settings.serverPort =
              Number.isFinite(n) && n >= 0 && n <= 65535
                ? n
                : DEFAULT_SETTINGS.serverPort;
            await this.plugin.saveSettings();
          })
      );

    const runtimePort = this.plugin.getRuntimePort();
    if (runtimePort !== null) {
      new Setting(containerEl)
        .setName("Current server URL")
        .setDesc(`http://127.0.0.1:${runtimePort}/sse — используйте этот порт в Cursor MCP config`);
    }

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
      .setName("Auto-reindex on change")
      .setDesc(
        "Обновлять индекс MCP после правок .md в vault — через 2 минуты без новых сохранений"
      )
      .addToggle((t) =>
        t.setValue(this.plugin.settings.autoReindexOnChange).onChange(async (v) => {
          this.plugin.settings.autoReindexOnChange = v;
          await this.plugin.saveSettings();
          this.plugin.setupVaultAutoIndex();
        })
      );

    new Setting(containerEl)
      .setName("Stop server on quit")
      .setDesc(
        "Остановить vault-server при закрытии Obsidian. Выключено — сервер остаётся для Cursor MCP в фоне."
      )
      .addToggle((t) =>
        t.setValue(this.plugin.settings.stopServerOnQuit).onChange(async (v) => {
          this.plugin.settings.stopServerOnQuit = v;
          await this.plugin.saveSettings();
        })
      );

    new Setting(containerEl)
      .setName("Index status")
      .setDesc(this.plugin.statusText)
      .addButton((btn) => {
        btn.setButtonText("Reindex").onClick(() => {
          void this.runAction(btn, "Reindex", () => this.plugin.reindexVault());
        });
      });

    new Setting(containerEl)
      .setName("Restart server")
      .setDesc("Перезапустить vault-server")
      .addButton((btn) => {
        btn.setButtonText("Restart").onClick(() => {
          void this.runAction(btn, "Restart", () => this.plugin.restartSidecarIfNeeded());
        });
      });

    new Setting(containerEl)
      .setName("Access scopes")
      .setDesc("Manage Cursor access to specific vault folders")
      .addButton((btn) => {
        btn.setButtonText("Open scopes").onClick(() => {
          void this.runAction(btn, "Open scopes", () => this.plugin.openScopesModal());
        });
      });
  }

  private async runAction(
    btn: { setDisabled: (v: boolean) => unknown; setButtonText: (t: string) => unknown },
    label: string,
    action: () => Promise<void>
  ): Promise<void> {
    btn.setDisabled(true);
    btn.setButtonText("…");
    try {
      await action();
      this.display();
    } catch (e) {
      new Notice(String(e));
      this.display();
    } finally {
      btn.setDisabled(false);
      btn.setButtonText(label);
    }
  }
}
