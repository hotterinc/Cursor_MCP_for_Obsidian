import { Notice, Setting } from "obsidian";
import { DEFAULT_OLLAMA_HOST, getActiveLlmConfig, type LlmPreset } from "./llmConfig";
import type ObsidianContextPlugin from "./main";
import type { LlmMode } from "./types";

function sleep(ms: number): Promise<void> {
  return new Promise((r) => window.setTimeout(r, ms));
}

export function renderLlmSettings(
  containerEl: HTMLElement,
  plugin: ObsidianContextPlugin
): void {
  containerEl.createEl("h3", { text: "Vault LLM" });

  const desc = containerEl.createDiv({ cls: "ocm-muted" });
  desc.setText(
    "Ответы по вашим заметкам: поиск по индексу + локальная LLM. " +
      "Preset — скачивание GGUF в plugin/data (Ollama не нужен). " +
      "Custom — внешний Ollama на localhost."
  );

  const progressEl = containerEl.createDiv({ cls: "ocm-llm-pull-progress" });
  const modelPickEl = containerEl.createDiv({ cls: "ocm-llm-model-pick" });
  const customEl = containerEl.createDiv({ cls: "ocm-llm-custom" });

  const refreshSections = () => {
    modelPickEl.empty();
    customEl.empty();
    progressEl.empty();

    if (plugin.settings.llmMode === "preset") {
      void renderPresetPicker(modelPickEl, plugin, progressEl, refreshSections);
    } else if (plugin.settings.llmMode === "custom") {
      renderCustomFields(customEl, plugin, progressEl, refreshSections);
    }
    void updateProgressDisplay(plugin, progressEl);
    plugin.refreshLlmRibbon();
  };

  new Setting(containerEl)
    .setName("Режим LLM")
    .setDesc("Off · Choose model (встроенное скачивание) · Custom (Ollama)")
    .addDropdown((dd) => {
      dd.addOption("off", "Off");
      dd.addOption("preset", "Choose model");
      dd.addOption("custom", "Custom");
      dd.setValue(plugin.settings.llmMode);
      dd.onChange(async (v) => {
        plugin.settings.llmMode = v as LlmMode;
        if (v === "off") {
          plugin.settings.llmModelReady = false;
        }
        await plugin.saveSettings();
        refreshSections();
      });
    });

  refreshSections();
}

async function renderPresetPicker(
  el: HTMLElement,
  plugin: ObsidianContextPlugin,
  progressEl: HTMLElement,
  refresh: () => void
): Promise<void> {
  try {
    if (!plugin.client) await plugin.startSidecarPublic();
    const client = plugin.ensureClientPublic();
    const { presets } = await client.llmPresets();

    const small = presets.filter((p) => p.tier === "small");
    const medium = presets.filter((p) => p.tier === "medium");

    el.createEl("p", { text: "Маленькие модели", cls: "ocm-llm-tier-label" });
    for (const p of small) {
      addPresetRow(el, plugin, p, progressEl, refresh);
    }
    el.createEl("p", { text: "Средние модели", cls: "ocm-llm-tier-label" });
    for (const p of medium) {
      addPresetRow(el, plugin, p, progressEl, refresh);
    }

    if (plugin.settings.llmPresetModel) {
      el.createEl("p", {
        cls: "ocm-muted",
        text: `Выбрано: ${plugin.settings.llmPresetModel}${
          plugin.settings.llmModelReady ? " ✓ готова" : " — нажмите Select для загрузки"
        }`,
      });
    }
  } catch (e) {
    el.createEl("p", { text: `Не удалось загрузить список моделей: ${e}` });
  }
}

function addPresetRow(
  el: HTMLElement,
  plugin: ObsidianContextPlugin,
  preset: LlmPreset,
  progressEl: HTMLElement,
  refresh: () => void
): void {
  const row = new Setting(el)
    .setName(preset.name)
    .setDesc(`${preset.description} · ${preset.sizeHint} · HuggingFace GGUF`);

  const selected = plugin.settings.llmPresetModel === preset.id;

  row.addButton((btn) => {
    btn.setButtonText(selected ? "Selected" : "Select");
    btn.setDisabled(selected && plugin.settings.llmModelReady);
    btn.onClick(async () => {
      plugin.settings.llmPresetModel = preset.id;
      plugin.settings.llmModelReady = false;
      await plugin.saveSettings();
      refresh();
      await startModelPull(plugin, "local", preset.id, progressEl, refresh);
    });
  });

  if (selected && !plugin.settings.llmModelReady) {
    row.addButton((btn) => {
      btn.setButtonText("Retry download");
      btn.onClick(async () => {
        await startModelPull(plugin, "local", preset.id, progressEl, refresh);
      });
    });
  }
}

function renderCustomFields(
  el: HTMLElement,
  plugin: ObsidianContextPlugin,
  progressEl: HTMLElement,
  refresh: () => void
): void {
  new Setting(el)
    .setName("Ollama host")
    .setDesc("Только localhost, например http://127.0.0.1:11434")
    .addText((text) =>
      text
        .setValue(plugin.settings.llmCustomHost || DEFAULT_OLLAMA_HOST)
        .onChange(async (v) => {
          plugin.settings.llmCustomHost = v.trim() || DEFAULT_OLLAMA_HOST;
          plugin.settings.llmModelReady = false;
          await plugin.saveSettings();
          plugin.refreshLlmRibbon();
        })
    );

  new Setting(el)
    .setName("Model name")
    .setDesc("Имя модели в Ollama, например qwen2.5:3b")
    .addText((text) =>
      text
        .setValue(plugin.settings.llmCustomModel)
        .onChange(async (v) => {
          plugin.settings.llmCustomModel = v.trim();
          plugin.settings.llmModelReady = false;
          await plugin.saveSettings();
          plugin.refreshLlmRibbon();
        })
    )
    .addButton((btn) => {
      btn.setButtonText("Download via Ollama");
      btn.onClick(async () => {
        const host = plugin.settings.llmCustomHost || DEFAULT_OLLAMA_HOST;
        const model = plugin.settings.llmCustomModel.trim();
        if (!model) {
          new Notice("Укажите имя модели");
          return;
        }
        await startModelPull(plugin, "ollama", model, progressEl, refresh, host);
      });
    });
}

async function startModelPull(
  plugin: ObsidianContextPlugin,
  backend: "local" | "ollama",
  model: string,
  progressEl: HTMLElement,
  refresh: () => void,
  host: string = DEFAULT_OLLAMA_HOST
): Promise<void> {
  try {
    if (!plugin.client) await plugin.startSidecarPublic();
    const client = plugin.ensureClientPublic();

    if (backend === "ollama") {
      const health = await client.llmStatus(host, model, "ollama");
      if (!health.health.ok) {
        new Notice(`Ollama недоступен: ${health.health.error ?? "запустите Ollama"}`);
        return;
      }
    }

    await client.llmPull(host, model, backend);
    new Notice(`Скачивание ${model}…`);
    while (true) {
      const p = await client.llmPullStatus();
      updateProgressEl(progressEl, p);
      if (!p.active) {
        if (p.error) {
          new Notice(`Ошибка загрузки: ${p.error}`);
          plugin.settings.llmModelReady = false;
        } else {
          plugin.settings.llmModelReady = true;
          new Notice(`Модель ${model} готова`);
        }
        await plugin.saveSettings();
        refresh();
        plugin.refreshLlmRibbon();
        break;
      }
      await sleep(600);
    }
  } catch (e) {
    new Notice(String(e));
  }
}

async function updateProgressDisplay(
  plugin: ObsidianContextPlugin,
  progressEl: HTMLElement
): Promise<void> {
  const cfg = getActiveLlmConfig(plugin.settings);
  if (!cfg || !plugin.client) return;
  try {
    const status = await plugin
      .ensureClientPublic()
      .llmStatus(cfg.host, cfg.model, cfg.backend);
    if (status.modelAvailable && !plugin.settings.llmModelReady) {
      plugin.settings.llmModelReady = true;
      await plugin.saveSettings();
      plugin.refreshLlmRibbon();
    }
    if (status.pull.active) {
      updateProgressEl(progressEl, status.pull);
    }
  } catch {
    /* ignore */
  }
}

function updateProgressEl(
  el: HTMLElement,
  p: { status: string; percent: number; error: string | null; active: boolean }
): void {
  el.empty();
  if (p.active || p.status === "success") {
    el.createEl("p", {
      text: p.active
        ? `Загрузка: ${p.status} ${p.percent > 0 ? `${p.percent}%` : ""}`
        : p.error
          ? `Ошибка: ${p.error}`
          : "Модель загружена",
    });
  }
}
