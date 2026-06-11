import { App, Modal, Notice, Setting } from "obsidian";
import type { SidecarClient } from "../sidecar/client";
import type { AccessScope } from "../types";

export class ScopesModal extends Modal {
  private scopes: AccessScope[] = [];

  constructor(app: App, private client: SidecarClient) {
    super(app);
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Access Scopes for Cursor" });
    contentEl.createEl("p", {
      text: "Each scope limits which folders Cursor can read via MCP. Copy the config snippet into Cursor settings.",
    });

    await this.reload();

    new Setting(contentEl)
      .setName("New scope")
      .addButton((btn) =>
        btn.setButtonText("Add scope").setCta().onClick(async () => {
          const id = `scope-${Date.now()}`;
          await this.client.upsertScope({
            id,
            name: "New scope",
            include: ["**/*.md"],
            exclude: [],
            writeAccess: false,
            canReindex: false,
            token: "",
          });
          await this.reload();
        })
      );

    this.listEl = contentEl.createDiv();
    this.renderList();
  }

  private listEl!: HTMLDivElement;

  private async reload() {
    const res = await this.client.listScopes();
    this.scopes = res.scopes;
  }

  private renderList() {
    this.listEl.empty();
    for (const scope of this.scopes) {
      const block = this.listEl.createDiv({ cls: "ocm-scope-block" });
      block.createEl("h3", { text: scope.name });

      new Setting(block)
        .setName("Scope ID")
        .setDesc(scope.id)
        .addText((t) => t.setValue(scope.id).setDisabled(true));

      new Setting(block)
        .setName("Include globs")
        .addTextArea((ta) =>
          ta
            .setValue(scope.include.join("\n"))
            .onChange(async (v) => {
              scope.include = v.split("\n").map((s) => s.trim()).filter(Boolean);
              await this.client.upsertScope(scope);
            })
        );

      new Setting(block)
        .setName("Write access")
        .addToggle((t) =>
          t.setValue(scope.writeAccess).onChange(async (v) => {
            scope.writeAccess = v;
            await this.client.upsertScope(scope);
          })
        );

      new Setting(block)
        .setName("Cursor MCP config")
        .addButton((btn) =>
          btn.setButtonText("Copy JSON").onClick(async () => {
            try {
              const res = await this.client.cursorConfig(scope.id);
              await navigator.clipboard.writeText(JSON.stringify(res.config, null, 2));
              new Notice("Cursor MCP config copied");
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
            new Notice("Token regenerated — update Cursor config");
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
  }

  onClose() {
    this.contentEl.empty();
  }
}
