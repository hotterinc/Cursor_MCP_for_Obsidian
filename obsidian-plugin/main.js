var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => ObsidianContextPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian6 = require("obsidian");

// src/sidecar/client.ts
var import_obsidian = require("obsidian");
var SidecarClient = class _SidecarClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }
  static fromRuntime(runtime) {
    return new _SidecarClient(`http://${runtime.host}:${runtime.port}`);
  }
  async request(path3, init) {
    const res = await (0, import_obsidian.requestUrl)({
      url: `${this.baseUrl}${path3}`,
      method: init?.method ?? "GET",
      headers: { "Content-Type": "application/json" },
      body: init?.body,
      throw: false
    });
    if (res.status >= 400) {
      throw new Error(`${res.status}: ${res.text}`);
    }
    return res.json;
  }
  health() {
    return this.request("/health");
  }
  status() {
    return this.request(
      "/api/v1/status"
    );
  }
  search(query, topK = 10) {
    return this.request("/api/v1/search", {
      method: "POST",
      body: JSON.stringify({ query, topK, mode: "hybrid" })
    });
  }
  reindex(mode = "incremental") {
    return this.request("/api/v1/reindex", {
      method: "POST",
      body: JSON.stringify({ mode })
    });
  }
  listScopes() {
    return this.request("/api/v1/scopes");
  }
  upsertScope(scope) {
    return this.request("/api/v1/scopes", {
      method: "POST",
      body: JSON.stringify(scope)
    });
  }
  deleteScope(scopeId) {
    return this.request(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}`,
      { method: "DELETE" }
    );
  }
  regenerateToken(scopeId) {
    return this.request(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}/regenerate-token`,
      { method: "POST" }
    );
  }
  cursorConfig(scopeId) {
    return this.request(
      `/api/v1/scopes/${encodeURIComponent(scopeId)}/cursor-config`
    );
  }
  scopePreview(scope) {
    return this.request("/api/v1/scopes/preview", {
      method: "POST",
      body: JSON.stringify(scope)
    });
  }
};

// src/sidecar/manager.ts
var import_child_process = require("child_process");
var fs2 = __toESM(require("fs"));
var path2 = __toESM(require("path"));
var import_obsidian2 = require("obsidian");

// src/paths.ts
var fs = __toESM(require("fs"));
var path = __toESM(require("path"));
function resolvePluginDir(app, manifest) {
  if (path.isAbsolute(manifest.dir)) {
    return manifest.dir;
  }
  const base = app.vault.adapter.basePath;
  if (!base) {
    throw new Error("\u041D\u0443\u0436\u0435\u043D \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault \u0441 basePath");
  }
  return path.join(base, ".obsidian", "plugins", manifest.id);
}
function resolvePluginDataDir(app, manifest) {
  return path.join(resolvePluginDir(app, manifest), "data");
}
function bundledSidecarPath(pluginDir) {
  const name = process.platform === "win32" ? "obsidian-context-mcp.exe" : "obsidian-context-mcp";
  return path.join(pluginDir, "bin", name);
}
function sidecarCandidates(pluginDir) {
  if (process.platform === "win32") {
    return [
      bundledSidecarPath(pluginDir),
      path.join(pluginDir, "server", ".venv", "Scripts", "obsidian-context-mcp.exe")
    ];
  }
  return [
    bundledSidecarPath(pluginDir),
    path.join(pluginDir, "server", ".venv", "bin", "obsidian-context-mcp")
  ];
}
function resolveSidecarCommand(pluginDir, pythonCommand) {
  for (const candidate of sidecarCandidates(pluginDir)) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return pythonCommand;
}
function hasBundledSidecar(pluginDir) {
  return sidecarCandidates(pluginDir).some((c) => fs.existsSync(c));
}
function activeSidecarPath(pluginDir, pythonCommand) {
  for (const candidate of sidecarCandidates(pluginDir)) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return pythonCommand.trim() || null;
}

// src/sidecar/manager.ts
async function healthCheck(url, timeoutMs) {
  try {
    const res = await Promise.race([
      (0, import_obsidian2.requestUrl)({ url, method: "GET", throw: false }),
      new Promise(
        (_, reject) => setTimeout(() => reject(new Error("timeout")), timeoutMs)
      )
    ]);
    return res.status >= 200 && res.status < 300;
  } catch {
    return false;
  }
}
function isPidAlive(pid) {
  if (!Number.isFinite(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}
var SidecarManager = class {
  constructor(vaultPath, pluginDir, dataDir, pythonCommand) {
    this.process = null;
    this.ownsProcess = false;
    this.vaultPath = vaultPath;
    this.pluginDir = path2.resolve(pluginDir);
    this.dataDir = path2.resolve(dataDir);
    this.pythonCommand = pythonCommand;
    fs2.mkdirSync(this.dataDir, { recursive: true });
  }
  get runtimePath() {
    return path2.join(this.dataDir, "runtime.json");
  }
  get lockPath() {
    return path2.join(this.dataDir, "locks", "vault-server.lock");
  }
  /** Stop our process and any orphaned vault-server for this vault (user-initiated restart). */
  async forceStopForRestart() {
    await this.stop();
    if (fs2.existsSync(this.lockPath)) {
      try {
        const pid = Number.parseInt(fs2.readFileSync(this.lockPath, "utf-8").trim(), 10);
        if (isPidAlive(pid)) {
          process.kill(pid, "SIGTERM");
          await new Promise((r) => setTimeout(r, 750));
        }
      } catch {
      }
      try {
        fs2.unlinkSync(this.lockPath);
      } catch {
      }
    }
    if (fs2.existsSync(this.runtimePath)) {
      try {
        fs2.unlinkSync(this.runtimePath);
      } catch {
      }
    }
  }
  async isHealthy(runtime) {
    return healthCheck(`http://${runtime.host}:${runtime.port}/health`, 2e3);
  }
  async start() {
    const existing = this.readRuntime();
    if (existing && await this.isHealthy(existing)) {
      this.ownsProcess = false;
      return existing;
    }
    return new Promise((resolve2, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        reject(err);
      };
      const command = resolveSidecarCommand(this.pluginDir, this.pythonCommand);
      try {
        this.process = (0, import_child_process.spawn)(
          command,
          [
            "vault-server",
            "--vault-path",
            this.vaultPath,
            "--data-dir",
            this.dataDir,
            "--host",
            "127.0.0.1",
            "--port",
            "0"
          ],
          { stdio: ["ignore", "pipe", "pipe"] }
        );
      } catch (err) {
        fail(err instanceof Error ? err : new Error(String(err)));
        return;
      }
      this.ownsProcess = true;
      this.process.on("error", (err) => {
        console.error("[vault-server] spawn error:", err);
        this.process = null;
        this.ownsProcess = false;
        fail(new Error(`\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u044C vault-server (${command}): ${err.message}`));
      });
      this.process.stdout?.on("data", (d) => console.log("[vault-server]", d.toString()));
      this.process.stderr?.on("data", (d) => console.error("[vault-server]", d.toString()));
      this.process.on("exit", (code) => {
        console.error(`[vault-server] exited with code ${code}`);
        this.process = null;
        this.ownsProcess = false;
        if (fs2.existsSync(this.runtimePath)) {
          try {
            fs2.unlinkSync(this.runtimePath);
          } catch {
          }
        }
        if (!settled) {
          fail(
            new Error(
              code === 1 ? "vault-server \u0443\u0436\u0435 \u0437\u0430\u043F\u0443\u0449\u0435\u043D \u0438\u043B\u0438 lock \u0437\u0430\u043D\u044F\u0442. \u041D\u0430\u0436\u043C\u0438\u0442\u0435 Restart server." : `vault-server \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043B\u0441\u044F \u0441 \u043A\u043E\u0434\u043E\u043C ${code}. \u0421\u043C. data/logs/vault-server.log`
            )
          );
        }
      });
      this.waitForRuntime(3e4).then((runtime) => {
        if (settled) return;
        settled = true;
        resolve2(runtime);
      }).catch(fail);
    });
  }
  async stop() {
    if (this.process && this.ownsProcess) {
      this.process.kill("SIGTERM");
      this.process = null;
      this.ownsProcess = false;
      if (fs2.existsSync(this.runtimePath)) {
        try {
          fs2.unlinkSync(this.runtimePath);
        } catch {
        }
      }
    }
  }
  readRuntime() {
    if (!fs2.existsSync(this.runtimePath)) return null;
    try {
      const raw = JSON.parse(fs2.readFileSync(this.runtimePath, "utf-8"));
      return {
        port: raw.port,
        pid: raw.pid,
        host: raw.host ?? "127.0.0.1",
        status: raw.status,
        startedAt: raw.started_at ?? raw.startedAt,
        vault_id: raw.vault_id ?? raw.vaultId
      };
    } catch {
      return null;
    }
  }
  waitForRuntime(timeoutMs) {
    const started = Date.now();
    return new Promise((resolve2, reject) => {
      const tick = () => {
        const runtime = this.readRuntime();
        if (runtime?.port) {
          resolve2(runtime);
          return;
        }
        if (Date.now() - started > timeoutMs) {
          reject(new Error("Timed out waiting for vault-server runtime.json"));
          return;
        }
        setTimeout(tick, 250);
      };
      tick();
    });
  }
};

// src/settings.ts
var import_obsidian3 = require("obsidian");

// src/types.ts
var DEFAULT_SETTINGS = {
  pythonCommand: "obsidian-context-mcp",
  sidecarArgs: "",
  autoStart: true
};

// src/settings.ts
var ObsidianContextSettingTab = class extends import_obsidian3.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Obsidian Context MCP" });
    const pluginDir = resolvePluginDir(this.app, this.plugin.manifest);
    const bundled = hasBundledSidecar(pluginDir);
    const serverPath = activeSidecarPath(pluginDir, this.plugin.settings.pythonCommand);
    new import_obsidian3.Setting(containerEl).setName("Program folder").setDesc(pluginDir);
    new import_obsidian3.Setting(containerEl).setName("Vault server").setDesc(
      bundled ? `\u0412\u0441\u0442\u0440\u043E\u0435\u043D \u0432 \u043F\u043B\u0430\u0433\u0438\u043D: ${serverPath}` : "\u0421\u0435\u0440\u0432\u0435\u0440 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D \u0432 plugin/. \u0417\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 scripts/install-obsidian-plugin.sh"
    );
    if (!bundled) {
      new import_obsidian3.Setting(containerEl).setName("Python command (dev fallback)").setDesc("\u0422\u043E\u043B\u044C\u043A\u043E \u0434\u043B\u044F \u0440\u0430\u0437\u0440\u0430\u0431\u043E\u0442\u043A\u0438, \u0435\u0441\u043B\u0438 server/.venv \u043D\u0435 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D").addText(
        (text) => text.setPlaceholder("obsidian-context-mcp").setValue(this.plugin.settings.pythonCommand).onChange(async (v) => {
          this.plugin.settings.pythonCommand = v.trim() || DEFAULT_SETTINGS.pythonCommand;
          await this.plugin.saveSettings();
        })
      );
    }
    new import_obsidian3.Setting(containerEl).setName("Auto-start sidecar").setDesc("Start vault-server when Obsidian loads the vault").addToggle(
      (t) => t.setValue(this.plugin.settings.autoStart).onChange(async (v) => {
        this.plugin.settings.autoStart = v;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian3.Setting(containerEl).setName("Index status").setDesc(this.plugin.statusText).addButton((btn) => {
      btn.setButtonText("Reindex").onClick(() => {
        void this.runAction(btn, "Reindex", () => this.plugin.reindexVault());
      });
    });
    new import_obsidian3.Setting(containerEl).setName("Restart server").setDesc("\u041F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u044C vault-server").addButton((btn) => {
      btn.setButtonText("Restart").onClick(() => {
        void this.runAction(btn, "Restart", () => this.plugin.restartSidecarIfNeeded());
      });
    });
    new import_obsidian3.Setting(containerEl).setName("Access scopes").setDesc("Manage Cursor access to specific vault folders").addButton((btn) => {
      btn.setButtonText("Open scopes").onClick(() => {
        void this.runAction(btn, "Open scopes", () => this.plugin.openScopesModal());
      });
    });
  }
  async runAction(btn, label, action) {
    btn.setDisabled(true);
    btn.setButtonText("\u2026");
    try {
      await action();
      this.display();
    } catch (e) {
      new import_obsidian3.Notice(String(e));
      this.display();
    } finally {
      btn.setDisabled(false);
      btn.setButtonText(label);
    }
  }
};

// src/views/ScopesModal.ts
var import_obsidian4 = require("obsidian");
var ScopesModal = class extends import_obsidian4.Modal {
  constructor(app, client) {
    super(app);
    this.client = client;
    this.scopes = [];
  }
  async onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Access Scopes for Cursor" });
    contentEl.createEl("p", {
      text: "Each scope limits which folders Cursor can read via MCP. Copy the config snippet into Cursor settings."
    });
    await this.reload();
    new import_obsidian4.Setting(contentEl).setName("New scope").addButton(
      (btn) => btn.setButtonText("Add scope").setCta().onClick(async () => {
        const id = `scope-${Date.now()}`;
        await this.client.upsertScope({
          id,
          name: "New scope",
          include: ["**/*.md"],
          exclude: [],
          writeAccess: false,
          canReindex: false,
          token: ""
        });
        await this.reload();
      })
    );
    this.listEl = contentEl.createDiv();
    this.renderList();
  }
  async reload() {
    const res = await this.client.listScopes();
    this.scopes = res.scopes;
  }
  renderList() {
    this.listEl.empty();
    for (const scope of this.scopes) {
      const block = this.listEl.createDiv({ cls: "ocm-scope-block" });
      block.createEl("h3", { text: scope.name });
      new import_obsidian4.Setting(block).setName("Scope ID").setDesc(scope.id).addText((t) => t.setValue(scope.id).setDisabled(true));
      new import_obsidian4.Setting(block).setName("Include globs").addTextArea(
        (ta) => ta.setValue(scope.include.join("\n")).onChange(async (v) => {
          scope.include = v.split("\n").map((s) => s.trim()).filter(Boolean);
          await this.client.upsertScope(scope);
        })
      );
      new import_obsidian4.Setting(block).setName("Write access").addToggle(
        (t) => t.setValue(scope.writeAccess).onChange(async (v) => {
          scope.writeAccess = v;
          await this.client.upsertScope(scope);
        })
      );
      new import_obsidian4.Setting(block).setName("Cursor MCP config").addButton(
        (btn) => btn.setButtonText("Copy JSON").onClick(async () => {
          try {
            const res = await this.client.cursorConfig(scope.id);
            await navigator.clipboard.writeText(JSON.stringify(res.config, null, 2));
            new import_obsidian4.Notice("Cursor MCP config copied");
          } catch (e) {
            new import_obsidian4.Notice(`Copy failed: ${e}`);
          }
        })
      ).addButton(
        (btn) => btn.setButtonText("Regenerate token").onClick(async () => {
          await this.client.regenerateToken(scope.id);
          await this.reload();
          this.renderList();
          new import_obsidian4.Notice("Token regenerated \u2014 update Cursor config");
        })
      ).addButton(
        (btn) => btn.setButtonText("Delete").setWarning().onClick(async () => {
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
};

// src/views/SearchModal.ts
var import_obsidian5 = require("obsidian");
var SearchModal = class extends import_obsidian5.Modal {
  constructor(app, client) {
    super(app);
    this.client = client;
    this.results = [];
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Semantic search" });
    let query = "";
    new import_obsidian5.Setting(contentEl).setName("Query").addText(
      (text) => text.setPlaceholder("Search vault...").onChange((v) => {
        query = v;
      })
    ).addButton(
      (btn) => btn.setButtonText("Search").setCta().onClick(async () => {
        try {
          const res = await this.client.search(query, 15);
          this.results = res.results;
          this.renderResults();
        } catch (e) {
          new import_obsidian5.Notice(`Search failed: ${e}`);
        }
      })
    );
    this.resultContainer = contentEl.createDiv({ cls: "ocm-search-results" });
  }
  renderResults() {
    this.resultContainer.empty();
    if (!this.results.length) {
      this.resultContainer.createEl("p", { text: "No results." });
      return;
    }
    for (const r of this.results) {
      const item = this.resultContainer.createDiv({ cls: "ocm-search-item" });
      item.createEl("strong", { text: `${r.title} (${(r.score * 100).toFixed(0)}%)` });
      item.createEl("div", { text: r.relative_path, cls: "ocm-muted" });
      item.createEl("p", { text: r.text.slice(0, 280) + (r.text.length > 280 ? "\u2026" : "") });
      item.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(r.relative_path);
        if (file) await this.app.workspace.getLeaf().openFile(file);
      };
    }
  }
  onClose() {
    this.contentEl.empty();
  }
};

// src/main.ts
var ObsidianContextPlugin = class extends import_obsidian6.Plugin {
  constructor() {
    super(...arguments);
    this.settings = DEFAULT_SETTINGS;
    this.sidecar = null;
    this.client = null;
    this.runtime = null;
    this.statusText = "Not started";
  }
  async onload() {
    try {
      await this.loadSettings();
      this.addSettingTab(new ObsidianContextSettingTab(this.app, this));
      const pluginDir = resolvePluginDir(this.app, this.manifest);
      const dataDir = resolvePluginDataDir(this.app, this.manifest);
      const vaultPath = this.getVaultPath();
      if (!vaultPath) {
        this.statusText = "\u041D\u0443\u0436\u0435\u043D \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault (\u043D\u0435 \u043E\u0431\u043B\u0430\u0447\u043D\u044B\u0439 \u0431\u0435\u0437 basePath)";
        new import_obsidian6.Notice("Obsidian Context MCP: \u043E\u0442\u043A\u0440\u043E\u0439 \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault \u0438\u043B\u0438 \u0443\u043A\u0430\u0436\u0438 Python command \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430\u0445.");
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
        callback: () => void this.openSearchModal()
      });
      this.addCommand({
        id: "ocm-reindex",
        name: "Reindex vault for MCP",
        callback: () => void this.reindexVault()
      });
      this.addCommand({
        id: "ocm-scopes",
        name: "Manage Cursor access scopes",
        callback: () => void this.openScopesModal()
      });
      this.addCommand({
        id: "ocm-restart-server",
        name: "Restart vault-server",
        callback: () => void this.restartSidecarIfNeeded()
      });
      const statusItem = this.addStatusBarItem();
      statusItem.setText("OCM");
      (0, import_obsidian6.setTooltip)(statusItem, this.statusText);
      statusItem.onClickEvent(() => void this.openSearchModal());
      if (this.settings.autoStart) {
        window.setTimeout(() => {
          void this.startSidecar().catch((e) => new import_obsidian6.Notice(String(e)));
        }, 500);
      }
    } catch (e) {
      console.error("[obsidian-context-mcp] onload failed:", e);
      this.statusText = `Plugin error: ${e}`;
      new import_obsidian6.Notice(`Obsidian Context MCP: \u043E\u0448\u0438\u0431\u043A\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438 \u2014 ${e}`);
    }
  }
  getVaultPath() {
    const adapter = this.app.vault.adapter;
    return adapter.basePath ?? null;
  }
  ensureSidecar() {
    if (this.sidecar) return this.sidecar;
    const vaultPath = this.getVaultPath();
    if (!vaultPath) {
      throw new Error("\u041D\u0443\u0436\u0435\u043D \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault (\u043D\u0435 \u043E\u0431\u043B\u0430\u0447\u043D\u044B\u0439 \u0431\u0435\u0437 basePath)");
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
  async restartSidecarIfNeeded() {
    const vaultPath = this.getVaultPath();
    if (!vaultPath) {
      throw new Error("\u041D\u0443\u0436\u0435\u043D \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault");
    }
    const sidecar = this.ensureSidecar();
    await sidecar.forceStopForRestart();
    this.client = null;
    this.runtime = null;
    await this.startSidecar();
    new import_obsidian6.Notice("vault-server \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0449\u0435\u043D");
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
  async startSidecar() {
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
  ensureClient() {
    if (!this.client) {
      throw new Error("vault-server is not running. Command palette \u2192 Restart vault-server");
    }
    return this.client;
  }
  async openSearchModal() {
    try {
      if (!this.client) await this.startSidecar();
      new SearchModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new import_obsidian6.Notice(String(e));
      throw e;
    }
  }
  async openScopesModal() {
    try {
      if (!this.client) await this.startSidecar();
      new ScopesModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new import_obsidian6.Notice(String(e));
      throw e;
    }
  }
  async reindexVault() {
    try {
      if (!this.client) await this.startSidecar();
      await this.ensureClient().reindex("incremental");
      const status = await this.client.status();
      this.statusText = `Indexed ${status.fileCount} files (${status.indexStatus})`;
      new import_obsidian6.Notice("Reindex started");
    } catch (e) {
      new import_obsidian6.Notice(String(e));
      throw e;
    }
  }
};
