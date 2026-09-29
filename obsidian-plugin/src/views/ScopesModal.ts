import { App, Modal, Notice, Setting } from "obsidian";
import { platform } from "os";
import { openCodexConfig, openEnvironmentVariables } from "./CodexSetupActions";
import { listVaultFolderNodes } from "../folderScope";
import type { SidecarClient } from "../sidecar/client";
import type { AccessScope } from "../types";
import { FolderScopePicker } from "./FolderScopePicker";

export class ScopesModal extends Modal {
  private pending = new Map<string, () => Promise<void>>();
  private saves = new Map<string, Promise<void>>();
  private scopes: AccessScope[] = [];
  private folderNodes = listVaultFolderNodes(this.app);
  private markdownPaths: string[] = [];

  constructor(app: App, private client: SidecarClient) {
    super(app);
  }

  async onOpen() {
    const { contentEl, modalEl } = this;
    modalEl.addClass("ocm-scopes-modal");
    modalEl.style.setProperty("--modal-width", "920px");
    modalEl.style.width = "min(920px, 94vw)";

    contentEl.addClass("ocm-scopes-modal-content");
    contentEl.createEl("h2", { text: "Доступ MCP к vault" });
    contentEl.createEl("p", {
      text: "Выберите папки для чтения и записи. Для Cursor скопируйте JSON, для локального Codex в приложении ChatGPT — TOML. Токен Codex задаётся через переменную окружения.",
    });

    this.markdownPaths = this.app.vault
      .getMarkdownFiles()
      .map((f) => f.path)
      .sort();

    this.listEl = contentEl.createDiv({ cls: "ocm-scopes-list" });

    new Setting(contentEl)
      .setName("Новый scope")
      .setDesc("Отдельный токен для Cursor и локального Codex с выбранными папками")
      .addButton((btn) =>
        btn.setButtonText("Добавить scope").setCta().onClick(() => {
          void this.addScope(btn);
        })
      );

    await this.reload();
    this.renderList();
  }

  private listEl!: HTMLDivElement;

  private async addScope(
    btn: { setDisabled: (v: boolean) => unknown; setButtonText: (t: string) => unknown }
  ): Promise<void> {
    const label = "Добавить scope";
    btn.setDisabled(true);
    btn.setButtonText("…");
    try {
      const id = `scope-${Date.now()}`;
      await this.client.upsertScope({
        id,
        name: "Новый scope",
        include: [],
        exclude: [],
        writeAccess: false,
        writeInclude: [],
        canReindex: false,
        token: "",
      });
      await this.reload();
      this.renderList();
      new Notice("Scope добавлен — выберите папки");
    } catch (e) {
      new Notice(`Не удалось добавить scope: ${e}`);
    } finally {
      btn.setDisabled(false);
      btn.setButtonText(label);
    }
  }

  private async reload() {
    const res = await this.client.listScopes();
    this.scopes = res.scopes;
  }

  private renderList() {
    this.listEl.empty();
    if (!this.scopes.length) {
      this.listEl.createEl("p", {
        cls: "ocm-muted",
        text: "Нет scopes. Нажмите «Добавить scope».",
      });
      return;
    }

    for (const scope of this.scopes) {
      this.renderScopeBlock(scope);
    }
  }

  private renderScopeBlock(scope: AccessScope) {
    const block = this.listEl.createDiv({ cls: "ocm-scope-block" });

    new Setting(block)
      .setName("Название")
      .addText((t) =>
        t.setValue(scope.name).onChange(async (v) => {
          scope.name = v.trim() || scope.name;
          await this.saveScope(scope);
        })
      );

    const pickerHost = block.createDiv({ cls: "ocm-folder-picker" });
    const previewEl = block.createEl("p", { cls: "ocm-muted" });

    let previewVersion = 0;
    const updatePreview = () => {
      const fields = picker.getScopeFields();
      const count = this.countFilesForInclude(fields.include, scope.exclude);
      const writeFolders = picker.getWriteFolderCount();
      const version = ++previewVersion;
      void this.client.scopePreview({ ...scope, ...fields, token: undefined }).then(result => {
        if (version === previewVersion) previewEl.setText(`MCP: ${result.fileCount} заметок` + (fields.writeAccess ? `, запись в ${writeFolders} папках` : ", только чтение"));
      }).catch(() => {});
      previewEl.setText(
        fields.include.length
          ? `MCP увидит ~${count} заметок` +
              (fields.writeAccess
                ? `, запись в ${writeFolders} ${writeFolders === 1 ? "папке" : "папках"}`
                : ", только чтение")
          : "Не выбрано ни одной папки — MCP не получит доступ к заметкам"
      );
    };

    const picker = new FolderScopePicker(
      pickerHost,
      this.folderNodes,
      scope.include,
      scope.writeInclude,
      scope.writeAccess
    );

    let saveTimer: number | null = null;
    const flush = async () => {
      if (saveTimer !== null) window.clearTimeout(saveTimer);
      saveTimer = null;
      await this.applyPicker(scope, picker);
    };
    this.pending.set(scope.id, flush);
    picker.onChange(() => {
      updatePreview();
      if (saveTimer !== null) window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(() => {
        void flush().catch((e) => new Notice(String(e)));
      }, 400);
    });
    updatePreview();

    new Setting(block)
      .setName("Scope ID")
      .setDesc(scope.id)
      .addText((t) => t.setValue(scope.id).setDisabled(true));

    const codexSetting = new Setting(block)
      .setName("Codex MCP")
      .setDesc("ChatGPT → Codex → Local: вставьте TOML в config.toml, задайте токен в переменных среды и перезапустите ChatGPT. Проверка: /mcp.")
      .addButton(btn => btn.setButtonText("Copy Codex config").onClick(async () => {
        try {
          await this.flushScope(scope.id);
          const res = await this.client.codexConfig(scope.id);
          await navigator.clipboard.writeText(res.config);
          new Notice("Конфиг Codex скопирован");
        } catch(e) { new Notice(String(e)); }
      }))
      .addButton(btn => btn.setButtonText("Copy scope token").onClick(async () => {
        try {
          await this.flushScope(scope.id);
          const res = await this.client.scopeToken(scope.id);
          await navigator.clipboard.writeText(res.token);
          new Notice(`Токен скопирован: задайте ${res.tokenEnvVar} перед запуском Codex`);
        } catch(e) { new Notice(String(e)); }
      }))
      .addButton(btn => btn.setButtonText("Open config.toml").onClick(async () => {
        try {
          const error = await openCodexConfig();
          if (error) new Notice(`Не удалось открыть конфигурацию: ${error}`);
        } catch (e) { new Notice(`Не удалось открыть конфигурацию: ${e}`); }
      }));
    codexSetting.settingEl.addClass("ocm-codex-setting");
    if (platform() === "win32") {
      codexSetting.addButton(btn => btn.setButtonText("Open env vars").onClick(() => {
        try {
          openEnvironmentVariables(error => new Notice(`Не удалось открыть переменные среды: ${error}`));
        } catch (e) { new Notice(`Не удалось открыть переменные среды: ${e}`); }
      }));
    }

    new Setting(block)
      .setName("Cursor MCP")
      .addButton((btn) =>
        btn.setButtonText("Copy JSON").onClick(async () => {
          try {
            await this.flushScope(scope.id);
            const res = await this.client.cursorConfig(scope.id);
            await navigator.clipboard.writeText(JSON.stringify(res.config, null, 2));
            new Notice("Конфиг Cursor скопирован");
          } catch (e) {
            new Notice(`Copy failed: ${e}`);
          }
        })
      )
      .addButton((btn) =>
        btn.setButtonText("Regenerate token").onClick(async () => {
          await this.flushScope(scope.id);
          await this.client.regenerateToken(scope.id);
          await this.reload();
          this.renderList();
          new Notice("Токен обновлён — обновите конфиг Cursor и переменную Codex");
        })
      )
      .addButton((btn) =>
        btn
          .setButtonText("Delete")
          .setWarning()
          .onClick(async () => {
            await this.flushScope(scope.id);
            this.pending.delete(scope.id);
            await this.client.deleteScope(scope.id);
            await this.reload();
            this.renderList();
          })
      );
  }

  private countFilesForInclude(include: string[], exclude: string[]): number {
    if (!include.length) return 0;

    let count = 0;
    for (const file of this.markdownPaths) {
      if (include.some((p) => this.fileMatchesGlob(file, p)) && !exclude.some(p => this.fileMatchesGlob(file, p))) count++;
    }
    return count;
  }

  private fileMatchesGlob(file: string, pattern: string): boolean {
    if (pattern === "**/*.md") return file.endsWith(".md");
    if (pattern !== "*.md" && pattern.endsWith("/*.md") && !pattern.endsWith("/**/*.md")) return file.slice(0, file.lastIndexOf("/")) === pattern.slice(0, -5);
    if (pattern === "*.md") return !file.includes("/");
    if (pattern.endsWith("/**")) {
      const prefix = pattern.slice(0, -3);
      return file === prefix || file.startsWith(`${prefix}/`);
    }
    if (pattern.endsWith("/**/*.md")) {
      const prefix = pattern.slice(0, -"/**/*.md".length);
      return file.startsWith(`${prefix}/`) || file === prefix;
    }
    return false;
  }

  private async applyPicker(scope: AccessScope, picker: FolderScopePicker) {
    const fields = picker.getScopeFields();
    scope.include = fields.include;
    scope.writeInclude = fields.writeInclude;
    scope.writeAccess = fields.writeAccess;
    await this.saveScope(scope);
  }

  private async saveScope(scope: AccessScope) {
    const previous = this.saves.get(scope.id) ?? Promise.resolve();
    const payload = { ...scope, token: undefined };
    const save = previous.catch(() => {}).then(async () => { await this.client.upsertScope(payload); });
    this.saves.set(scope.id, save);
    await save;
  }

  private async flushScope(id: string) {
    await this.pending.get(id)?.();
    await this.saves.get(id);
  }

  onClose() {
    for (const id of this.pending.keys()) void this.flushScope(id).catch(e => new Notice(`Scope save failed: ${e}`));
    this.contentEl.empty();
  }
}
