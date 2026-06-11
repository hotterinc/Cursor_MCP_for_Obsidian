import { App, Modal, Notice, Setting } from "obsidian";
import { getActiveLlmConfig } from "../llmConfig";
import type { SidecarClient } from "../sidecar/client";
import type { LlmAskSource } from "../llmConfig";
import type ObsidianContextPlugin from "../main";

export class LlmSearchModal extends Modal {
  constructor(
    app: App,
    private plugin: ObsidianContextPlugin,
    private client: SidecarClient
  ) {
    super(app);
  }

  onOpen() {
    const cfg = getActiveLlmConfig(this.plugin.settings);
    if (!cfg) {
      new Notice("LLM не настроен. Settings → Obsidian Context MCP → Vault LLM");
      this.close();
      return;
    }

    const { contentEl, modalEl } = this;
    modalEl.addClass("ocm-llm-modal");
    contentEl.createEl("h2", { text: "Спросить vault (LLM)" });
    contentEl.createEl("p", {
      cls: "ocm-muted",
      text: `Модель: ${cfg.model} · поиск по индексу + локальный ответ`,
    });

    let query = "";
    new Setting(contentEl)
      .setName("Вопрос")
      .addText((text) =>
        text
          .setPlaceholder("Как настроить scopes для Cursor?")
          .onChange((v) => {
            query = v;
          })
      )
      .addButton((btn) =>
        btn.setButtonText("Спросить").setCta().onClick(() => void this.runAsk(query, btn))
      );

    this.answerEl = contentEl.createDiv({ cls: "ocm-llm-answer" });
    this.sourcesEl = contentEl.createDiv({ cls: "ocm-llm-sources" });
  }

  private answerEl!: HTMLDivElement;
  private sourcesEl!: HTMLDivElement;

  private async runAsk(
    query: string,
    btn: { setDisabled: (v: boolean) => unknown; setButtonText: (t: string) => unknown }
  ) {
    const cfg = getActiveLlmConfig(this.plugin.settings);
    if (!cfg) return;
    const q = query.trim();
    if (!q) {
      new Notice("Введите вопрос");
      return;
    }

    btn.setDisabled(true);
    btn.setButtonText("…");
    this.answerEl.empty();
    this.sourcesEl.empty();
    this.answerEl.createEl("p", { text: "Думаю… (может занять минуту на CPU)" });

    try {
      const res = await this.client.llmAsk(q, cfg.host, cfg.model, cfg.backend);
      this.answerEl.empty();
      this.answerEl.createEl("div", { cls: "ocm-llm-answer-text", text: res.answer });
      this.renderSources(res.sources);
    } catch (e) {
      this.answerEl.empty();
      this.answerEl.createEl("p", { text: String(e), cls: "ocm-llm-error" });
      new Notice(String(e));
    } finally {
      btn.setDisabled(false);
      btn.setButtonText("Спросить");
    }
  }

  private renderSources(sources: LlmAskSource[]) {
    this.sourcesEl.empty();
    if (!sources.length) return;
    this.sourcesEl.createEl("h3", { text: "Источники" });
    for (const s of sources) {
      const item = this.sourcesEl.createDiv({ cls: "ocm-search-item" });
      item.createEl("strong", {
        text: `${s.title} (${(s.score * 100).toFixed(0)}%)`,
      });
      item.createEl("div", { text: s.relative_path, cls: "ocm-muted" });
      if (s.excerpt) {
        item.createEl("p", { text: s.excerpt + (s.excerpt.length >= 200 ? "…" : "") });
      }
      item.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(s.relative_path);
        if (file) await this.app.workspace.getLeaf().openFile(file as any);
      };
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}
