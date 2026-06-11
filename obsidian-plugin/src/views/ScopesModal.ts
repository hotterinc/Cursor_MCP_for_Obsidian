import { App, Modal, Notice, Setting } from "obsidian";
import { listVaultFolderNodes } from "../folderScope";
import type { SidecarClient } from "../sidecar/client";
import type { AccessScope } from "../types";
import { FolderScopePicker } from "./FolderScopePicker";

export class ScopesModal extends Modal {
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
    contentEl.createEl("h2", { text: "Доступ Cursor к vault" });
    contentEl.createEl("p", {
      text: "Выберите папки для чтения и записи. Скопируйте JSON в настройки MCP Cursor.",
    });

    this.markdownPaths = this.app.vault
      .getMarkdownFiles()
      .map((f) => f.path)
      .sort();

    this.listEl = contentEl.createDiv({ cls: "ocm-scopes-list" });

    new Setting(contentEl)
      .setName("Новый scope")
      .setDesc("Отдельный токен для Cursor с выбранными папками")
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

    const updatePreview = () => {
      const fields = picker.getScopeFields();
      const count = this.countFilesForInclude(fields.include);
      const writeFolders = picker.getWriteFolderCount();
      previewEl.setText(
        fields.include.length
          ? `Cursor увидит ~${count} заметок` +
              (fields.writeAccess
                ? `, запись в ${writeFolders} ${writeFolders === 1 ? "папке" : "папках"}`
                : ", только чтение")
          : "Не выбрано ни одной папки — Cursor ничего не увидит"
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
    picker.onChange(() => {
      updatePreview();
      if (saveTimer !== null) window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(() => {
        void this.applyPicker(scope, picker).catch((e) => new Notice(String(e)));
      }, 400);
    });
    updatePreview();

    new Setting(block)
      .setName("Scope ID")
      .setDesc(scope.id)
      .addText((t) => t.setValue(scope.id).setDisabled(true));

    new Setting(block)
      .setName("Cursor MCP")
      .addButton((btn) =>
        btn.setButtonText("Copy JSON").onClick(async () => {
          try {
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
          await this.client.regenerateToken(scope.id);
          await this.reload();
          this.renderList();
          new Notice("Токен обновлён — обновите конфиг в Cursor");
        })
      )
      .addButton((btn) =>
        btn
          .setButtonText("Delete")
          .setWarning()
          .onClick(async () => {
            await this.client.deleteScope(scope.id);
            await this.reload();
            this.renderList();
          })
      );
  }

  private countFilesForInclude(include: string[]): number {
    if (!include.length) return 0;
    if (include.includes("**/*.md")) return this.markdownPaths.length;
    let count = 0;
    for (const file of this.markdownPaths) {
      if (include.some((p) => this.fileMatchesGlob(file, p))) count++;
    }
    return count;
  }

  private fileMatchesGlob(file: string, pattern: string): boolean {
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
    await this.client.upsertScope(scope);
  }

  onClose() {
    this.contentEl.empty();
  }
}
