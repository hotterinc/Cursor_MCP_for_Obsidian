import { App, Modal, Notice, Setting } from "obsidian";
import type { SidecarClient } from "../sidecar/client";
import type { SearchResult } from "../types";

export class SearchModal extends Modal {
  private results: SearchResult[] = [];

  constructor(app: App, private client: SidecarClient) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Semantic search" });

    let query = "";
    new Setting(contentEl)
      .setName("Query")
      .addText((text) =>
        text.setPlaceholder("Search vault...").onChange((v) => {
          query = v;
        })
      )
      .addButton((btn) =>
        btn.setButtonText("Search").setCta().onClick(async () => {
          try {
            const res = await this.client.search(query, 15);
            this.results = res.results;
            this.renderResults();
          } catch (e) {
            new Notice(`Search failed: ${e}`);
          }
        })
      );

    this.resultContainer = contentEl.createDiv({ cls: "ocm-search-results" });
  }

  private resultContainer!: HTMLDivElement;

  private renderResults() {
    this.resultContainer.empty();
    if (!this.results.length) {
      this.resultContainer.createEl("p", { text: "No results." });
      return;
    }
    for (const r of this.results) {
      const item = this.resultContainer.createDiv({ cls: "ocm-search-item" });
      item.createEl("strong", { text: `${r.title} (${(r.score * 100).toFixed(0)}%)` });
      item.createEl("div", { text: r.relative_path, cls: "ocm-muted" });
      item.createEl("p", { text: r.text.slice(0, 280) + (r.text.length > 280 ? "…" : "") });
      item.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(r.relative_path);
        if (file) await this.app.workspace.getLeaf().openFile(file as any);
      };
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}
