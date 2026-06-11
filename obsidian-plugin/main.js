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
var import_obsidian10 = require("obsidian");

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
    return this.request("/api/v1/status");
  }
  indexJobStatus() {
    return this.status().then((s) => s.job);
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
  indexFile(relativePath) {
    return this.request("/api/v1/index-file", {
      method: "POST",
      body: JSON.stringify({ relativePath })
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
  llmPresets() {
    return this.request("/api/v1/llm/presets");
  }
  llmStatus(host, model, backend = "local") {
    const q = new URLSearchParams({ host, model, backend });
    return this.request(`/api/v1/llm/status?${q}`);
  }
  llmPull(host, model, backend = "local") {
    return this.request("/api/v1/llm/pull", {
      method: "POST",
      body: JSON.stringify({ host, model, backend })
    });
  }
  llmPullStatus() {
    return this.request("/api/v1/llm/pull-status");
  }
  llmAsk(query, host, model, backend = "local", topK = 8) {
    return this.request("/api/v1/llm/ask", {
      method: "POST",
      body: JSON.stringify({ query, host, model, backend, topK })
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
var SIDECAR_STARTUP_TIMEOUT_MS = 12e4;
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
function clearMacQuarantine(binaryPath) {
  if (process.platform !== "darwin" || !fs2.existsSync(binaryPath)) return;
  try {
    const probe = (0, import_child_process.spawnSync)("xattr", ["-p", "com.apple.quarantine", binaryPath], {
      encoding: "utf-8"
    });
    if (probe.status === 0) {
      (0, import_child_process.spawnSync)("xattr", ["-d", "com.apple.quarantine", binaryPath]);
    }
  } catch {
  }
}
function unlinkIfExists(filePath) {
  try {
    if (fs2.existsSync(filePath)) {
      fs2.unlinkSync(filePath);
    }
  } catch {
  }
}
function logVaultServerLine(text, stream) {
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const isError = stream === "stderr" && /\b(ERROR|Error:|Traceback|Exception|failed)\b/.test(trimmed) && !/^INFO:/.test(trimmed);
    if (isError) {
      console.error("[vault-server]", trimmed);
    } else {
      console.log("[vault-server]", trimmed);
    }
  }
}
var SidecarManager = class {
  constructor(vaultPath, pluginDir, dataDir, pythonCommand, serverPort) {
    this.process = null;
    this.ownsProcess = false;
    this.startPromise = null;
    this.vaultPath = vaultPath;
    this.pluginDir = path2.resolve(pluginDir);
    this.dataDir = path2.resolve(dataDir);
    this.pythonCommand = pythonCommand;
    this.serverPort = serverPort;
    fs2.mkdirSync(this.dataDir, { recursive: true });
  }
  get runtimePath() {
    return path2.join(this.dataDir, "runtime.json");
  }
  get lockPath() {
    return path2.join(this.dataDir, "locks", "vault-server.lock");
  }
  readLockPid() {
    if (!fs2.existsSync(this.lockPath)) return null;
    try {
      const pid = Number.parseInt(fs2.readFileSync(this.lockPath, "utf-8").trim(), 10);
      return Number.isFinite(pid) && pid > 0 ? pid : null;
    } catch {
      return null;
    }
  }
  collectServerPids() {
    const pids = /* @__PURE__ */ new Set();
    const lockPid = this.readLockPid();
    if (lockPid) pids.add(lockPid);
    const runtime = this.readRuntime();
    if (runtime?.pid) pids.add(runtime.pid);
    if (this.process?.pid) pids.add(this.process.pid);
    return [...pids];
  }
  async terminatePid(pid, timeoutMs = 5e3) {
    if (!isPidAlive(pid)) return;
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      return;
    }
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      if (!isPidAlive(pid)) return;
      await new Promise((r) => setTimeout(r, 200));
    }
    try {
      process.kill(pid, "SIGKILL");
    } catch {
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  /** Stop every vault-server instance tied to this vault data dir. */
  async clearServerState() {
    for (const pid of this.collectServerPids()) {
      await this.terminatePid(pid);
    }
    this.process = null;
    this.ownsProcess = false;
    unlinkIfExists(this.lockPath);
    unlinkIfExists(this.runtimePath);
  }
  async forceStopForRestart() {
    this.startPromise = null;
    await this.clearServerState();
  }
  async isHealthy(runtime) {
    return healthCheck(`http://${runtime.host}:${runtime.port}/health`, 2e3);
  }
  async prepareForStart() {
    const existing = this.readRuntime();
    if (existing && await this.isHealthy(existing)) {
      this.ownsProcess = false;
      return existing;
    }
    const lockPid = this.readLockPid();
    if (lockPid && isPidAlive(lockPid)) {
      await this.clearServerState();
    } else {
      unlinkIfExists(this.lockPath);
      if (!existing) {
        unlinkIfExists(this.runtimePath);
      }
    }
    return null;
  }
  async start() {
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.startOnce().finally(() => {
      this.startPromise = null;
    });
    return this.startPromise;
  }
  async startOnce() {
    const attached = await this.prepareForStart();
    if (attached) return attached;
    return new Promise((resolve2, reject) => {
      let settled = false;
      const fail = (err) => {
        if (settled) return;
        settled = true;
        reject(err);
      };
      const command = resolveSidecarCommand(this.pluginDir, this.pythonCommand);
      clearMacQuarantine(command);
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
            String(this.serverPort)
          ],
          {
            stdio: ["ignore", "pipe", "pipe"],
            detached: true,
            env: {
              ...process.env,
              TOKENIZERS_PARALLELISM: "false",
              OMP_NUM_THREADS: "1"
            }
          }
        );
        this.process.unref();
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
      this.process.stdout?.on("data", (d) => logVaultServerLine(d.toString(), "stdout"));
      this.process.stderr?.on("data", (d) => logVaultServerLine(d.toString(), "stderr"));
      this.process.on("exit", (code) => {
        this.process = null;
        this.ownsProcess = false;
        if (!settled) {
          console.error(`[vault-server] exited with code ${code}`);
          fail(
            new Error(
              code === 1 ? "vault-server \u043D\u0435 \u0441\u043C\u043E\u0433 \u0437\u0430\u0445\u0432\u0430\u0442\u0438\u0442\u044C lock. \u041D\u0430\u0436\u043C\u0438\u0442\u0435 Restart server \u0435\u0449\u0451 \u0440\u0430\u0437." : `vault-server \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043B\u0441\u044F \u0441 \u043A\u043E\u0434\u043E\u043C ${code}. \u0421\u043C. data/logs/vault-server.log`
            )
          );
        } else if (code !== 0) {
          console.warn(`[vault-server] exited with code ${code}`);
        }
      });
      this.waitForHealthyRuntime(SIDECAR_STARTUP_TIMEOUT_MS).then((runtime) => {
        if (settled) return;
        settled = true;
        this.process?.stdout?.removeAllListeners("data");
        this.process?.stderr?.removeAllListeners("data");
        this.process?.removeAllListeners("exit");
        this.process = null;
        this.ownsProcess = false;
        resolve2(runtime);
      }).catch(fail);
    });
  }
  async stop() {
    if (this.process && this.ownsProcess) {
      await this.terminatePid(this.process.pid ?? 0);
      this.process = null;
      this.ownsProcess = false;
      unlinkIfExists(this.runtimePath);
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
  /** Attach when server outlived the startup waiter (e.g. slow first launch). */
  async tryAttachRunning() {
    const runtime = this.readRuntime();
    if (runtime?.port && await this.isHealthy(runtime)) {
      this.ownsProcess = false;
      this.process = null;
      return runtime;
    }
    return null;
  }
  waitForHealthyRuntime(timeoutMs) {
    const started = Date.now();
    return new Promise((resolve2, reject) => {
      const tick = () => {
        void (async () => {
          const runtime = this.readRuntime();
          if (runtime?.port && await this.isHealthy(runtime)) {
            resolve2(runtime);
            return;
          }
          if (Date.now() - started > timeoutMs) {
            const late = this.readRuntime();
            if (late?.port && await this.isHealthy(late)) {
              resolve2(late);
              return;
            }
            reject(
              new Error(
                "Timed out waiting for vault-server HTTP endpoint (\u043F\u0435\u0440\u0432\u044B\u0439 \u0437\u0430\u043F\u0443\u0441\u043A \u043C\u043E\u0436\u0435\u0442 \u0437\u0430\u043D\u044F\u0442\u044C \u0434\u043E 2 \u043C\u0438\u043D)"
              )
            );
            return;
          }
          setTimeout(tick, 250);
        })();
      };
      tick();
    });
  }
};

// src/llmConfig.ts
var DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434";
function getActiveLlmConfig(settings) {
  if (settings.llmMode === "off") return null;
  if (settings.llmMode === "preset") {
    if (!settings.llmPresetModel) return null;
    return { backend: "local", host: DEFAULT_OLLAMA_HOST, model: settings.llmPresetModel };
  }
  const host = settings.llmCustomHost?.trim() || DEFAULT_OLLAMA_HOST;
  const model = settings.llmCustomModel?.trim();
  if (!model) return null;
  return { backend: "ollama", host, model };
}
function isLlmUiEnabled(settings) {
  return settings.llmMode !== "off" && Boolean(getActiveLlmConfig(settings));
}

// src/reindexProgress.ts
var import_obsidian3 = require("obsidian");
var MILESTONES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
function progressPercent(job) {
  if (!job.total_files) return 0;
  return Math.min(100, Math.floor(job.files_scanned / job.total_files * 100));
}
function notifyMilestones(job, notified) {
  const pct = progressPercent(job);
  const total = job.total_files;
  const scanned = job.files_scanned;
  for (const m of MILESTONES) {
    if (pct >= m && !notified.has(m)) {
      notified.add(m);
      const detail = total > 0 ? ` (\u043E\u0431\u0440\u0430\u0431\u043E\u0442\u0430\u043D\u043E ${scanned}/${total})` : "";
      new import_obsidian3.Notice(`\u0418\u043D\u0434\u0435\u043A\u0441\u0430\u0446\u0438\u044F: ${m}%${detail}`);
    }
  }
}
function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}
async function watchReindexProgress(poll, timeoutMs = 36e5) {
  const notified = /* @__PURE__ */ new Set();
  const started = Date.now();
  new import_obsidian3.Notice("\u0418\u043D\u0434\u0435\u043A\u0441\u0430\u0446\u0438\u044F: \u0441\u0442\u0430\u0440\u0442\u2026");
  while (Date.now() - started < timeoutMs) {
    const job = await poll();
    if (!job) {
      await sleep(400);
      continue;
    }
    notifyMilestones(job, notified);
    if (job.status === "completed") {
      if (!notified.has(100)) {
        notified.add(100);
        new import_obsidian3.Notice(
          `\u0418\u043D\u0434\u0435\u043A\u0441\u0430\u0446\u0438\u044F: 100% \u2014 \u043E\u0431\u0440\u0430\u0431\u043E\u0442\u0430\u043D\u043E ${job.files_scanned}/${job.total_files} (${job.files_indexed} \u043D\u043E\u0432\u044B\u0445, ${job.files_skipped} \u0431\u0435\u0437 \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u0439${job.files_failed ? `, ${job.files_failed} \u043E\u0448\u0438\u0431\u043E\u043A` : ""})`
        );
      }
      return job;
    }
    if (job.status === "failed" || job.status === "cancelled") {
      new import_obsidian3.Notice(
        `\u0418\u043D\u0434\u0435\u043A\u0441\u0430\u0446\u0438\u044F \u043E\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0430: ${job.status}${job.error ? ` \u2014 ${job.error}` : ""}`
      );
      return job;
    }
    await sleep(400);
  }
  new import_obsidian3.Notice("\u0418\u043D\u0434\u0435\u043A\u0441\u0430\u0446\u0438\u044F: \u043F\u0440\u0435\u0432\u044B\u0448\u0435\u043D\u043E \u0432\u0440\u0435\u043C\u044F \u043E\u0436\u0438\u0434\u0430\u043D\u0438\u044F");
  return null;
}
function formatIndexStatus(indexed, total, indexStatus) {
  if (total > indexed) {
    return `Indexed ${indexed}/${total} files (${indexStatus})`;
  }
  return `Indexed ${indexed} files (${indexStatus})`;
}

// src/settings.ts
var import_obsidian5 = require("obsidian");

// src/llmSettings.ts
var import_obsidian4 = require("obsidian");
function sleep2(ms) {
  return new Promise((r) => window.setTimeout(r, ms));
}
function renderLlmSettings(containerEl, plugin) {
  containerEl.createEl("h3", { text: "Vault LLM" });
  const desc = containerEl.createDiv({ cls: "ocm-muted" });
  desc.setText(
    "\u041E\u0442\u0432\u0435\u0442\u044B \u043F\u043E \u0432\u0430\u0448\u0438\u043C \u0437\u0430\u043C\u0435\u0442\u043A\u0430\u043C: \u043F\u043E\u0438\u0441\u043A \u043F\u043E \u0438\u043D\u0434\u0435\u043A\u0441\u0443 + \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u0430\u044F LLM. Preset \u2014 \u0441\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435 GGUF \u0432 plugin/data (Ollama \u043D\u0435 \u043D\u0443\u0436\u0435\u043D). Custom \u2014 \u0432\u043D\u0435\u0448\u043D\u0438\u0439 Ollama \u043D\u0430 localhost."
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
  new import_obsidian4.Setting(containerEl).setName("\u0420\u0435\u0436\u0438\u043C LLM").setDesc("Off \xB7 Choose model (\u0432\u0441\u0442\u0440\u043E\u0435\u043D\u043D\u043E\u0435 \u0441\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435) \xB7 Custom (Ollama)").addDropdown((dd) => {
    dd.addOption("off", "Off");
    dd.addOption("preset", "Choose model");
    dd.addOption("custom", "Custom");
    dd.setValue(plugin.settings.llmMode);
    dd.onChange(async (v) => {
      plugin.settings.llmMode = v;
      if (v === "off") {
        plugin.settings.llmModelReady = false;
      }
      await plugin.saveSettings();
      refreshSections();
    });
  });
  refreshSections();
}
async function renderPresetPicker(el, plugin, progressEl, refresh) {
  try {
    if (!plugin.client) await plugin.startSidecarPublic();
    const client = plugin.ensureClientPublic();
    const { presets } = await client.llmPresets();
    const small = presets.filter((p) => p.tier === "small");
    const medium = presets.filter((p) => p.tier === "medium");
    el.createEl("p", { text: "\u041C\u0430\u043B\u0435\u043D\u044C\u043A\u0438\u0435 \u043C\u043E\u0434\u0435\u043B\u0438", cls: "ocm-llm-tier-label" });
    for (const p of small) {
      addPresetRow(el, plugin, p, progressEl, refresh);
    }
    el.createEl("p", { text: "\u0421\u0440\u0435\u0434\u043D\u0438\u0435 \u043C\u043E\u0434\u0435\u043B\u0438", cls: "ocm-llm-tier-label" });
    for (const p of medium) {
      addPresetRow(el, plugin, p, progressEl, refresh);
    }
    if (plugin.settings.llmPresetModel) {
      el.createEl("p", {
        cls: "ocm-muted",
        text: `\u0412\u044B\u0431\u0440\u0430\u043D\u043E: ${plugin.settings.llmPresetModel}${plugin.settings.llmModelReady ? " \u2713 \u0433\u043E\u0442\u043E\u0432\u0430" : " \u2014 \u043D\u0430\u0436\u043C\u0438\u0442\u0435 Select \u0434\u043B\u044F \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438"}`
      });
    }
  } catch (e) {
    el.createEl("p", { text: `\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044C \u0441\u043F\u0438\u0441\u043E\u043A \u043C\u043E\u0434\u0435\u043B\u0435\u0439: ${e}` });
  }
}
function addPresetRow(el, plugin, preset, progressEl, refresh) {
  const row = new import_obsidian4.Setting(el).setName(preset.name).setDesc(`${preset.description} \xB7 ${preset.sizeHint} \xB7 HuggingFace GGUF`);
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
function renderCustomFields(el, plugin, progressEl, refresh) {
  new import_obsidian4.Setting(el).setName("Ollama host").setDesc("\u0422\u043E\u043B\u044C\u043A\u043E localhost, \u043D\u0430\u043F\u0440\u0438\u043C\u0435\u0440 http://127.0.0.1:11434").addText(
    (text) => text.setValue(plugin.settings.llmCustomHost || DEFAULT_OLLAMA_HOST).onChange(async (v) => {
      plugin.settings.llmCustomHost = v.trim() || DEFAULT_OLLAMA_HOST;
      plugin.settings.llmModelReady = false;
      await plugin.saveSettings();
      plugin.refreshLlmRibbon();
    })
  );
  new import_obsidian4.Setting(el).setName("Model name").setDesc("\u0418\u043C\u044F \u043C\u043E\u0434\u0435\u043B\u0438 \u0432 Ollama, \u043D\u0430\u043F\u0440\u0438\u043C\u0435\u0440 qwen2.5:3b").addText(
    (text) => text.setValue(plugin.settings.llmCustomModel).onChange(async (v) => {
      plugin.settings.llmCustomModel = v.trim();
      plugin.settings.llmModelReady = false;
      await plugin.saveSettings();
      plugin.refreshLlmRibbon();
    })
  ).addButton((btn) => {
    btn.setButtonText("Download via Ollama");
    btn.onClick(async () => {
      const host = plugin.settings.llmCustomHost || DEFAULT_OLLAMA_HOST;
      const model = plugin.settings.llmCustomModel.trim();
      if (!model) {
        new import_obsidian4.Notice("\u0423\u043A\u0430\u0436\u0438\u0442\u0435 \u0438\u043C\u044F \u043C\u043E\u0434\u0435\u043B\u0438");
        return;
      }
      await startModelPull(plugin, "ollama", model, progressEl, refresh, host);
    });
  });
}
async function startModelPull(plugin, backend, model, progressEl, refresh, host = DEFAULT_OLLAMA_HOST) {
  try {
    if (!plugin.client) await plugin.startSidecarPublic();
    const client = plugin.ensureClientPublic();
    if (backend === "ollama") {
      const health = await client.llmStatus(host, model, "ollama");
      if (!health.health.ok) {
        new import_obsidian4.Notice(`Ollama \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D: ${health.health.error ?? "\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 Ollama"}`);
        return;
      }
    }
    await client.llmPull(host, model, backend);
    new import_obsidian4.Notice(`\u0421\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435 ${model}\u2026`);
    while (true) {
      const p = await client.llmPullStatus();
      updateProgressEl(progressEl, p);
      if (!p.active) {
        if (p.error) {
          new import_obsidian4.Notice(`\u041E\u0448\u0438\u0431\u043A\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438: ${p.error}`);
          plugin.settings.llmModelReady = false;
        } else {
          plugin.settings.llmModelReady = true;
          new import_obsidian4.Notice(`\u041C\u043E\u0434\u0435\u043B\u044C ${model} \u0433\u043E\u0442\u043E\u0432\u0430`);
        }
        await plugin.saveSettings();
        refresh();
        plugin.refreshLlmRibbon();
        break;
      }
      await sleep2(600);
    }
  } catch (e) {
    new import_obsidian4.Notice(String(e));
  }
}
async function updateProgressDisplay(plugin, progressEl) {
  const cfg = getActiveLlmConfig(plugin.settings);
  if (!cfg || !plugin.client) return;
  try {
    const status = await plugin.ensureClientPublic().llmStatus(cfg.host, cfg.model, cfg.backend);
    if (status.modelAvailable && !plugin.settings.llmModelReady) {
      plugin.settings.llmModelReady = true;
      await plugin.saveSettings();
      plugin.refreshLlmRibbon();
    }
    if (status.pull.active) {
      updateProgressEl(progressEl, status.pull);
    }
  } catch {
  }
}
function updateProgressEl(el, p) {
  el.empty();
  if (p.active || p.status === "success") {
    el.createEl("p", {
      text: p.active ? `\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430: ${p.status} ${p.percent > 0 ? `${p.percent}%` : ""}` : p.error ? `\u041E\u0448\u0438\u0431\u043A\u0430: ${p.error}` : "\u041C\u043E\u0434\u0435\u043B\u044C \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043D\u0430"
    });
  }
}

// src/types.ts
var DEFAULT_SETTINGS = {
  pythonCommand: "obsidian-context-mcp",
  sidecarArgs: "",
  autoStart: true,
  serverPort: 18432,
  autoReindexOnChange: true,
  stopServerOnQuit: false,
  llmMode: "off",
  llmPresetModel: "",
  llmCustomHost: "http://127.0.0.1:11434",
  llmCustomModel: "",
  llmModelReady: false
};

// src/settings.ts
var ObsidianContextSettingTab = class extends import_obsidian5.PluginSettingTab {
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
    new import_obsidian5.Setting(containerEl).setName("Program folder").setDesc(pluginDir);
    new import_obsidian5.Setting(containerEl).setName("Vault server").setDesc(
      bundled ? `\u0412\u0441\u0442\u0440\u043E\u0435\u043D \u0432 \u043F\u043B\u0430\u0433\u0438\u043D: ${serverPath}` : "\u0421\u0435\u0440\u0432\u0435\u0440 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D \u0432 plugin/. \u0417\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 scripts/install-obsidian-plugin.sh"
    );
    if (!bundled) {
      new import_obsidian5.Setting(containerEl).setName("Python command (dev fallback)").setDesc("\u0422\u043E\u043B\u044C\u043A\u043E \u0434\u043B\u044F \u0440\u0430\u0437\u0440\u0430\u0431\u043E\u0442\u043A\u0438, \u0435\u0441\u043B\u0438 server/.venv \u043D\u0435 \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D").addText(
        (text) => text.setPlaceholder("obsidian-context-mcp").setValue(this.plugin.settings.pythonCommand).onChange(async (v) => {
          this.plugin.settings.pythonCommand = v.trim() || DEFAULT_SETTINGS.pythonCommand;
          await this.plugin.saveSettings();
        })
      );
    }
    new import_obsidian5.Setting(containerEl).setName("MCP server port").setDesc(
      "\u0424\u0438\u043A\u0441\u0438\u0440\u043E\u0432\u0430\u043D\u043D\u044B\u0439 \u043F\u043E\u0440\u0442 \u0434\u043B\u044F Cursor MCP (\u043F\u043E \u0443\u043C\u043E\u043B\u0447\u0430\u043D\u0438\u044E 18432). 0 = \u0441\u043B\u0443\u0447\u0430\u0439\u043D\u044B\u0439 \u043F\u043E\u0440\u0442 \u043F\u0440\u0438 \u043A\u0430\u0436\u0434\u043E\u043C \u0437\u0430\u043F\u0443\u0441\u043A\u0435 \u2014 \u0442\u043E\u0433\u0434\u0430 \u043F\u043E\u0441\u043B\u0435 \u0440\u0435\u0441\u0442\u0430\u0440\u0442\u0430 \u043D\u0443\u0436\u043D\u043E \u043E\u0431\u043D\u043E\u0432\u043B\u044F\u0442\u044C .cursor/mcp.json. \u041F\u043E\u0441\u043B\u0435 \u0441\u043C\u0435\u043D\u044B \u043F\u043E\u0440\u0442\u0430 \u043D\u0430\u0436\u043C\u0438\u0442\u0435 Restart server."
    ).addText(
      (text) => text.setPlaceholder("18432").setValue(String(this.plugin.settings.serverPort)).onChange(async (v) => {
        const n = Number.parseInt(v.trim(), 10);
        this.plugin.settings.serverPort = Number.isFinite(n) && n >= 0 && n <= 65535 ? n : DEFAULT_SETTINGS.serverPort;
        await this.plugin.saveSettings();
      })
    );
    const runtimePort = this.plugin.getRuntimePort();
    if (runtimePort !== null) {
      new import_obsidian5.Setting(containerEl).setName("Current server URL").setDesc(`http://127.0.0.1:${runtimePort}/sse \u2014 \u0438\u0441\u043F\u043E\u043B\u044C\u0437\u0443\u0439\u0442\u0435 \u044D\u0442\u043E\u0442 \u043F\u043E\u0440\u0442 \u0432 Cursor MCP config`);
    }
    new import_obsidian5.Setting(containerEl).setName("Auto-start sidecar").setDesc("Start vault-server when Obsidian loads the vault").addToggle(
      (t) => t.setValue(this.plugin.settings.autoStart).onChange(async (v) => {
        this.plugin.settings.autoStart = v;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian5.Setting(containerEl).setName("Auto-reindex on change").setDesc(
      "\u041E\u0431\u043D\u043E\u0432\u043B\u044F\u0442\u044C \u0438\u043D\u0434\u0435\u043A\u0441 MCP \u043F\u043E\u0441\u043B\u0435 \u043F\u0440\u0430\u0432\u043E\u043A .md \u0432 vault \u2014 \u0447\u0435\u0440\u0435\u0437 2 \u043C\u0438\u043D\u0443\u0442\u044B \u0431\u0435\u0437 \u043D\u043E\u0432\u044B\u0445 \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u0438\u0439"
    ).addToggle(
      (t) => t.setValue(this.plugin.settings.autoReindexOnChange).onChange(async (v) => {
        this.plugin.settings.autoReindexOnChange = v;
        await this.plugin.saveSettings();
        this.plugin.setupVaultAutoIndex();
      })
    );
    new import_obsidian5.Setting(containerEl).setName("Stop server on quit").setDesc(
      "\u041E\u0441\u0442\u0430\u043D\u043E\u0432\u0438\u0442\u044C vault-server \u043F\u0440\u0438 \u0437\u0430\u043A\u0440\u044B\u0442\u0438\u0438 Obsidian. \u0412\u044B\u043A\u043B\u044E\u0447\u0435\u043D\u043E \u2014 \u0441\u0435\u0440\u0432\u0435\u0440 \u043E\u0441\u0442\u0430\u0451\u0442\u0441\u044F \u0434\u043B\u044F Cursor MCP \u0432 \u0444\u043E\u043D\u0435."
    ).addToggle(
      (t) => t.setValue(this.plugin.settings.stopServerOnQuit).onChange(async (v) => {
        this.plugin.settings.stopServerOnQuit = v;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian5.Setting(containerEl).setName("Index status").setDesc(this.plugin.statusText).addButton((btn) => {
      btn.setButtonText("Reindex").onClick(() => {
        void this.runAction(btn, "Reindex", () => this.plugin.reindexVault());
      });
    });
    new import_obsidian5.Setting(containerEl).setName("Restart server").setDesc("\u041F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u044C vault-server").addButton((btn) => {
      btn.setButtonText("Restart").onClick(() => {
        void this.runAction(btn, "Restart", () => this.plugin.restartSidecarIfNeeded());
      });
    });
    new import_obsidian5.Setting(containerEl).setName("Access scopes").setDesc("Manage Cursor access to specific vault folders").addButton((btn) => {
      btn.setButtonText("Open scopes").onClick(() => {
        void this.runAction(btn, "Open scopes", () => this.plugin.openScopesModal());
      });
    });
    renderLlmSettings(containerEl, this.plugin);
  }
  async runAction(btn, label, action) {
    btn.setDisabled(true);
    btn.setButtonText("\u2026");
    try {
      await action();
      this.display();
    } catch (e) {
      new import_obsidian5.Notice(String(e));
      this.display();
    } finally {
      btn.setDisabled(false);
      btn.setButtonText(label);
    }
  }
};

// src/views/ScopesModal.ts
var import_obsidian6 = require("obsidian");

// src/folderScope.ts
var ALL_VAULT_PATH = "*";
var SKIP_PREFIXES = [".obsidian", ".trash", ".git"];
function listVaultFolderNodes(app) {
  const nodes = [
    { path: ALL_VAULT_PATH, name: "\u0412\u0435\u0441\u044C vault", depth: 0 },
    { path: "", name: "\u0424\u0430\u0439\u043B\u044B \u0432 \u043A\u043E\u0440\u043D\u0435 (\u0431\u0435\u0437 \u043F\u0430\u043F\u043A\u0438)", depth: 1 }
  ];
  const folders = app.vault.getAllFolders(true).sort((a, b) => a.path.localeCompare(b.path));
  for (const folder of folders) {
    const p = folder.path.replace(/\\/g, "/").replace(/^\/+/, "");
    if (!p || p === "/") continue;
    if (SKIP_PREFIXES.some((skip) => p === skip || p.startsWith(`${skip}/`))) continue;
    nodes.push({
      path: p,
      name: folder.name,
      depth: p.split("/").length + 1
    });
  }
  return nodes;
}
function cascadeTargets(nodes, path3) {
  if (path3 === ALL_VAULT_PATH) {
    return nodes.map((n) => n.path);
  }
  if (!path3) {
    return [""];
  }
  const prefix = `${path3}/`;
  return nodes.filter((n) => n.path === path3 || n.path.startsWith(prefix)).map((n) => n.path);
}
function folderToIncludeGlob(path3) {
  if (path3 === ALL_VAULT_PATH) return "**/*.md";
  return path3 ? `${path3}/**` : "*.md";
}
function globToFolderPath(pattern) {
  const p = pattern.trim().replace(/\\/g, "/");
  if (p === "**/*.md" || p === "**/**") return ALL_VAULT_PATH;
  if (p === "*.md") return "";
  if (p.endsWith("/**")) return p.slice(0, -3);
  if (p.endsWith("/**/*.md")) return p.slice(0, -"/**/*.md".length);
  return null;
}
function isFullVaultGlob(patterns) {
  return patterns.some((p) => p === "**/*.md" || p === "**/**");
}
function selectionsFromScope(nodes, include, writeInclude, writeAccess) {
  const map = /* @__PURE__ */ new Map();
  for (const n of nodes) {
    map.set(n.path, { read: false, write: false });
  }
  if (isFullVaultGlob(include)) {
    for (const n of nodes) {
      map.set(n.path, { read: true, write: false });
    }
  } else {
    for (const pattern of include) {
      const folder = globToFolderPath(pattern);
      if (folder === null || !map.has(folder)) continue;
      for (const target of cascadeTargets(nodes, folder)) {
        const cur = map.get(target);
        map.set(target, { read: true, write: cur.write });
      }
    }
  }
  const writePatterns = writeInclude?.length ? writeInclude : writeAccess ? include : [];
  if (isFullVaultGlob(writePatterns)) {
    for (const n of nodes) {
      map.set(n.path, { read: true, write: true });
    }
  } else {
    for (const pattern of writePatterns) {
      const folder = globToFolderPath(pattern);
      if (folder === null || !map.has(folder)) continue;
      for (const target of cascadeTargets(nodes, folder)) {
        map.set(target, { read: true, write: true });
      }
    }
  }
  syncMasterRow(nodes, map);
  return map;
}
function syncMasterRow(nodes, map) {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  map.set(ALL_VAULT_PATH, {
    read: rest.every((n) => map.get(n.path)?.read),
    write: rest.every((n) => map.get(n.path)?.write)
  });
}
function scopeFromSelections(nodes, selections) {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  const allRead = rest.every((n) => selections.get(n.path)?.read);
  const allWrite = rest.every((n) => selections.get(n.path)?.write);
  if (allRead) {
    return {
      include: ["**/*.md"],
      writeInclude: allWrite ? ["**/*.md"] : compactWriteGlobs(nodes, selections),
      writeAccess: allWrite || compactWriteGlobs(nodes, selections).length > 0
    };
  }
  const include = [];
  const writeInclude = [];
  for (const node of rest) {
    const access = selections.get(node.path);
    if (!access?.read) continue;
    if (!isCoveredByAncestor(node.path, rest, selections, "read")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob) include.push(glob);
    }
    if (access.write && !isCoveredByAncestor(node.path, rest, selections, "write")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob && glob !== "**/*.md") writeInclude.push(glob);
      else if (glob === "*.md") writeInclude.push("*.md");
    }
  }
  return {
    include,
    writeInclude,
    writeAccess: writeInclude.length > 0
  };
}
function isCoveredByAncestor(path3, nodes, selections, field) {
  if (!path3) return false;
  const parts = path3.split("/");
  for (let i = 1; i < parts.length; i++) {
    const ancestor = parts.slice(0, i).join("/");
    if (nodes.some((n) => n.path === ancestor) && selections.get(ancestor)?.[field]) {
      return true;
    }
  }
  return false;
}
function compactWriteGlobs(nodes, selections) {
  const rest = nodes.filter((n) => n.path !== ALL_VAULT_PATH);
  const out = [];
  for (const node of rest) {
    const access = selections.get(node.path);
    if (!access?.write) continue;
    if (!isCoveredByAncestor(node.path, rest, selections, "write")) {
      const glob = folderToIncludeGlob(node.path);
      if (glob && glob !== "**/*.md") out.push(glob);
    }
  }
  return out;
}

// src/views/FolderScopePicker.ts
var FolderScopePicker = class {
  constructor(container, nodes, include, writeInclude, writeAccess) {
    this.container = container;
    this.nodes = nodes;
    this.selections = /* @__PURE__ */ new Map();
    this.bodyEl = null;
    this.checkboxByPath = /* @__PURE__ */ new Map();
    this.selections = selectionsFromScope(nodes, include, writeInclude, writeAccess);
    this.render();
  }
  onChange(handler) {
    this.onChangeHandler = handler;
  }
  getScopeFields() {
    return scopeFromSelections(this.nodes, this.selections);
  }
  getWriteFolderCount() {
    let n = 0;
    for (const [path3, access] of this.selections) {
      if (path3 !== ALL_VAULT_PATH && access.write) n++;
    }
    return n;
  }
  getAccess(path3) {
    return this.selections.get(path3) ?? { read: false, write: false };
  }
  setCascade(path3, field, value) {
    const targets = cascadeTargets(this.nodes, path3);
    for (const target of targets) {
      const cur = this.getAccess(target);
      if (field === "read") {
        this.selections.set(target, {
          read: value,
          write: value ? cur.write : false
        });
      } else {
        this.selections.set(target, {
          read: value ? true : cur.read,
          write: value
        });
      }
    }
    syncMasterRow(this.nodes, this.selections);
    this.syncCheckboxes();
    this.onChangeHandler?.();
  }
  syncCheckboxes() {
    for (const node of this.nodes) {
      const refs = this.checkboxByPath.get(node.path);
      if (!refs) continue;
      const access = this.getAccess(node.path);
      refs.read.checked = access.read;
      refs.write.checked = access.write;
      refs.write.disabled = !access.read;
    }
  }
  render() {
    this.container.empty();
    this.checkboxByPath.clear();
    this.container.createEl("p", {
      cls: "ocm-muted",
      text: "\u0413\u0430\u043B\u043E\u0447\u043A\u0430 \u043D\u0430 \u043F\u0430\u043F\u043A\u0435 \u0432\u043A\u043B\u044E\u0447\u0430\u0435\u0442 \u0432\u0441\u0435 \u043F\u043E\u0434\u043F\u0430\u043F\u043A\u0438. \xAB\u0412\u0435\u0441\u044C vault\xBB \u2014 \u0432\u0441\u0435 \u0441\u0440\u0430\u0437\u0443."
    });
    const header = this.container.createDiv({ cls: "ocm-folder-picker-header" });
    header.createSpan({ text: "\u041F\u0430\u043F\u043A\u0430" });
    header.createSpan({ text: "\u0427\u0438\u0442\u0430\u0442\u044C", cls: "ocm-folder-picker-col" });
    header.createSpan({ text: "\u041F\u0438\u0441\u0430\u0442\u044C", cls: "ocm-folder-picker-col" });
    this.bodyEl = this.container.createDiv({ cls: "ocm-folder-picker-body" });
    for (const node of this.nodes) {
      const access = this.getAccess(node.path);
      const row = this.bodyEl.createDiv({ cls: "ocm-folder-picker-row" });
      if (node.path === ALL_VAULT_PATH) {
        row.addClass("ocm-folder-picker-master");
      }
      row.style.paddingLeft = `${8 + node.depth * 18}px`;
      const label = row.createDiv({ cls: "ocm-folder-picker-label" });
      label.createSpan({ text: node.name });
      if (node.path && node.path !== ALL_VAULT_PATH) {
        label.createEl("span", { cls: "ocm-muted", text: ` ${node.path}` });
      }
      const readCb = row.createEl("input", { type: "checkbox" });
      readCb.className = "ocm-folder-picker-col";
      readCb.checked = access.read;
      const writeCb = row.createEl("input", { type: "checkbox" });
      writeCb.className = "ocm-folder-picker-col";
      writeCb.checked = access.write;
      writeCb.disabled = !access.read;
      readCb.onchange = () => {
        this.setCascade(node.path, "read", readCb.checked);
      };
      writeCb.onchange = () => {
        this.setCascade(node.path, "write", writeCb.checked);
      };
      this.checkboxByPath.set(node.path, { read: readCb, write: writeCb });
    }
  }
};

// src/views/ScopesModal.ts
var ScopesModal = class extends import_obsidian6.Modal {
  constructor(app, client) {
    super(app);
    this.client = client;
    this.scopes = [];
    this.folderNodes = listVaultFolderNodes(this.app);
    this.markdownPaths = [];
  }
  async onOpen() {
    const { contentEl, modalEl } = this;
    modalEl.addClass("ocm-scopes-modal");
    modalEl.style.setProperty("--modal-width", "920px");
    modalEl.style.width = "min(920px, 94vw)";
    contentEl.addClass("ocm-scopes-modal-content");
    contentEl.createEl("h2", { text: "\u0414\u043E\u0441\u0442\u0443\u043F Cursor \u043A vault" });
    contentEl.createEl("p", {
      text: "\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u043F\u0430\u043F\u043A\u0438 \u0434\u043B\u044F \u0447\u0442\u0435\u043D\u0438\u044F \u0438 \u0437\u0430\u043F\u0438\u0441\u0438. \u0421\u043A\u043E\u043F\u0438\u0440\u0443\u0439\u0442\u0435 JSON \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 MCP Cursor."
    });
    this.markdownPaths = this.app.vault.getMarkdownFiles().map((f) => f.path).sort();
    this.listEl = contentEl.createDiv({ cls: "ocm-scopes-list" });
    new import_obsidian6.Setting(contentEl).setName("\u041D\u043E\u0432\u044B\u0439 scope").setDesc("\u041E\u0442\u0434\u0435\u043B\u044C\u043D\u044B\u0439 \u0442\u043E\u043A\u0435\u043D \u0434\u043B\u044F Cursor \u0441 \u0432\u044B\u0431\u0440\u0430\u043D\u043D\u044B\u043C\u0438 \u043F\u0430\u043F\u043A\u0430\u043C\u0438").addButton(
      (btn) => btn.setButtonText("\u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C scope").setCta().onClick(() => {
        void this.addScope(btn);
      })
    );
    await this.reload();
    this.renderList();
  }
  async addScope(btn) {
    const label = "\u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C scope";
    btn.setDisabled(true);
    btn.setButtonText("\u2026");
    try {
      const id = `scope-${Date.now()}`;
      await this.client.upsertScope({
        id,
        name: "\u041D\u043E\u0432\u044B\u0439 scope",
        include: [],
        exclude: [],
        writeAccess: false,
        writeInclude: [],
        canReindex: false,
        token: ""
      });
      await this.reload();
      this.renderList();
      new import_obsidian6.Notice("Scope \u0434\u043E\u0431\u0430\u0432\u043B\u0435\u043D \u2014 \u0432\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u043F\u0430\u043F\u043A\u0438");
    } catch (e) {
      new import_obsidian6.Notice(`\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0434\u043E\u0431\u0430\u0432\u0438\u0442\u044C scope: ${e}`);
    } finally {
      btn.setDisabled(false);
      btn.setButtonText(label);
    }
  }
  async reload() {
    const res = await this.client.listScopes();
    this.scopes = res.scopes;
  }
  renderList() {
    this.listEl.empty();
    if (!this.scopes.length) {
      this.listEl.createEl("p", {
        cls: "ocm-muted",
        text: "\u041D\u0435\u0442 scopes. \u041D\u0430\u0436\u043C\u0438\u0442\u0435 \xAB\u0414\u043E\u0431\u0430\u0432\u0438\u0442\u044C scope\xBB."
      });
      return;
    }
    for (const scope of this.scopes) {
      this.renderScopeBlock(scope);
    }
  }
  renderScopeBlock(scope) {
    const block = this.listEl.createDiv({ cls: "ocm-scope-block" });
    new import_obsidian6.Setting(block).setName("\u041D\u0430\u0437\u0432\u0430\u043D\u0438\u0435").addText(
      (t) => t.setValue(scope.name).onChange(async (v) => {
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
        fields.include.length ? `Cursor \u0443\u0432\u0438\u0434\u0438\u0442 ~${count} \u0437\u0430\u043C\u0435\u0442\u043E\u043A` + (fields.writeAccess ? `, \u0437\u0430\u043F\u0438\u0441\u044C \u0432 ${writeFolders} ${writeFolders === 1 ? "\u043F\u0430\u043F\u043A\u0435" : "\u043F\u0430\u043F\u043A\u0430\u0445"}` : ", \u0442\u043E\u043B\u044C\u043A\u043E \u0447\u0442\u0435\u043D\u0438\u0435") : "\u041D\u0435 \u0432\u044B\u0431\u0440\u0430\u043D\u043E \u043D\u0438 \u043E\u0434\u043D\u043E\u0439 \u043F\u0430\u043F\u043A\u0438 \u2014 Cursor \u043D\u0438\u0447\u0435\u0433\u043E \u043D\u0435 \u0443\u0432\u0438\u0434\u0438\u0442"
      );
    };
    const picker = new FolderScopePicker(
      pickerHost,
      this.folderNodes,
      scope.include,
      scope.writeInclude,
      scope.writeAccess
    );
    let saveTimer = null;
    picker.onChange(() => {
      updatePreview();
      if (saveTimer !== null) window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(() => {
        void this.applyPicker(scope, picker).catch((e) => new import_obsidian6.Notice(String(e)));
      }, 400);
    });
    updatePreview();
    new import_obsidian6.Setting(block).setName("Scope ID").setDesc(scope.id).addText((t) => t.setValue(scope.id).setDisabled(true));
    new import_obsidian6.Setting(block).setName("Cursor MCP").addButton(
      (btn) => btn.setButtonText("Copy JSON").onClick(async () => {
        try {
          const res = await this.client.cursorConfig(scope.id);
          await navigator.clipboard.writeText(JSON.stringify(res.config, null, 2));
          new import_obsidian6.Notice("\u041A\u043E\u043D\u0444\u0438\u0433 Cursor \u0441\u043A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u043D");
        } catch (e) {
          new import_obsidian6.Notice(`Copy failed: ${e}`);
        }
      })
    ).addButton(
      (btn) => btn.setButtonText("Regenerate token").onClick(async () => {
        await this.client.regenerateToken(scope.id);
        await this.reload();
        this.renderList();
        new import_obsidian6.Notice("\u0422\u043E\u043A\u0435\u043D \u043E\u0431\u043D\u043E\u0432\u043B\u0451\u043D \u2014 \u043E\u0431\u043D\u043E\u0432\u0438\u0442\u0435 \u043A\u043E\u043D\u0444\u0438\u0433 \u0432 Cursor");
      })
    ).addButton(
      (btn) => btn.setButtonText("Delete").setWarning().onClick(async () => {
        await this.client.deleteScope(scope.id);
        await this.reload();
        this.renderList();
      })
    );
  }
  countFilesForInclude(include) {
    if (!include.length) return 0;
    if (include.includes("**/*.md")) return this.markdownPaths.length;
    let count = 0;
    for (const file of this.markdownPaths) {
      if (include.some((p) => this.fileMatchesGlob(file, p))) count++;
    }
    return count;
  }
  fileMatchesGlob(file, pattern) {
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
  async applyPicker(scope, picker) {
    const fields = picker.getScopeFields();
    scope.include = fields.include;
    scope.writeInclude = fields.writeInclude;
    scope.writeAccess = fields.writeAccess;
    await this.saveScope(scope);
  }
  async saveScope(scope) {
    await this.client.upsertScope(scope);
  }
  onClose() {
    this.contentEl.empty();
  }
};

// src/views/SearchModal.ts
var import_obsidian7 = require("obsidian");
var SearchModal = class extends import_obsidian7.Modal {
  constructor(app, client) {
    super(app);
    this.client = client;
    this.results = [];
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Semantic search" });
    let query = "";
    new import_obsidian7.Setting(contentEl).setName("Query").addText(
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
          new import_obsidian7.Notice(`Search failed: ${e}`);
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

// src/views/LlmSearchModal.ts
var import_obsidian8 = require("obsidian");
var LlmSearchModal = class extends import_obsidian8.Modal {
  constructor(app, plugin, client) {
    super(app);
    this.plugin = plugin;
    this.client = client;
  }
  onOpen() {
    const cfg = getActiveLlmConfig(this.plugin.settings);
    if (!cfg) {
      new import_obsidian8.Notice("LLM \u043D\u0435 \u043D\u0430\u0441\u0442\u0440\u043E\u0435\u043D. Settings \u2192 Obsidian Context MCP \u2192 Vault LLM");
      this.close();
      return;
    }
    const { contentEl, modalEl } = this;
    modalEl.addClass("ocm-llm-modal");
    contentEl.createEl("h2", { text: "\u0421\u043F\u0440\u043E\u0441\u0438\u0442\u044C vault (LLM)" });
    contentEl.createEl("p", {
      cls: "ocm-muted",
      text: `\u041C\u043E\u0434\u0435\u043B\u044C: ${cfg.model} \xB7 \u043F\u043E\u0438\u0441\u043A \u043F\u043E \u0438\u043D\u0434\u0435\u043A\u0441\u0443 + \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 \u043E\u0442\u0432\u0435\u0442`
    });
    let query = "";
    new import_obsidian8.Setting(contentEl).setName("\u0412\u043E\u043F\u0440\u043E\u0441").addText(
      (text) => text.setPlaceholder("\u041A\u0430\u043A \u043D\u0430\u0441\u0442\u0440\u043E\u0438\u0442\u044C scopes \u0434\u043B\u044F Cursor?").onChange((v) => {
        query = v;
      })
    ).addButton(
      (btn) => btn.setButtonText("\u0421\u043F\u0440\u043E\u0441\u0438\u0442\u044C").setCta().onClick(() => void this.runAsk(query, btn))
    );
    this.answerEl = contentEl.createDiv({ cls: "ocm-llm-answer" });
    this.sourcesEl = contentEl.createDiv({ cls: "ocm-llm-sources" });
  }
  async runAsk(query, btn) {
    const cfg = getActiveLlmConfig(this.plugin.settings);
    if (!cfg) return;
    const q = query.trim();
    if (!q) {
      new import_obsidian8.Notice("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0432\u043E\u043F\u0440\u043E\u0441");
      return;
    }
    btn.setDisabled(true);
    btn.setButtonText("\u2026");
    this.answerEl.empty();
    this.sourcesEl.empty();
    this.answerEl.createEl("p", { text: "\u0414\u0443\u043C\u0430\u044E\u2026 (\u043C\u043E\u0436\u0435\u0442 \u0437\u0430\u043D\u044F\u0442\u044C \u043C\u0438\u043D\u0443\u0442\u0443 \u043D\u0430 CPU)" });
    try {
      const res = await this.client.llmAsk(q, cfg.host, cfg.model, cfg.backend);
      this.answerEl.empty();
      this.answerEl.createEl("div", { cls: "ocm-llm-answer-text", text: res.answer });
      this.renderSources(res.sources);
    } catch (e) {
      this.answerEl.empty();
      this.answerEl.createEl("p", { text: String(e), cls: "ocm-llm-error" });
      new import_obsidian8.Notice(String(e));
    } finally {
      btn.setDisabled(false);
      btn.setButtonText("\u0421\u043F\u0440\u043E\u0441\u0438\u0442\u044C");
    }
  }
  renderSources(sources) {
    this.sourcesEl.empty();
    if (!sources.length) return;
    this.sourcesEl.createEl("h3", { text: "\u0418\u0441\u0442\u043E\u0447\u043D\u0438\u043A\u0438" });
    for (const s of sources) {
      const item = this.sourcesEl.createDiv({ cls: "ocm-search-item" });
      item.createEl("strong", {
        text: `${s.title} (${(s.score * 100).toFixed(0)}%)`
      });
      item.createEl("div", { text: s.relative_path, cls: "ocm-muted" });
      if (s.excerpt) {
        item.createEl("p", { text: s.excerpt + (s.excerpt.length >= 200 ? "\u2026" : "") });
      }
      item.onclick = async () => {
        const file = this.app.vault.getAbstractFileByPath(s.relative_path);
        if (file) await this.app.workspace.getLeaf().openFile(file);
      };
    }
  }
  onClose() {
    this.contentEl.empty();
  }
};

// src/vaultAutoIndex.ts
var import_obsidian9 = require("obsidian");
var AUTO_INDEX_IDLE_MS = 2 * 60 * 1e3;
var SKIP_PREFIXES2 = [".obsidian/", ".trash/"];
function shouldIndex(path3) {
  const p = path3.replace(/\\/g, "/");
  if (!p.toLowerCase().endsWith(".md")) return false;
  return !SKIP_PREFIXES2.some((pre) => p.startsWith(pre));
}
var VaultAutoIndexer = class {
  constructor(app, getClient, idleMs = AUTO_INDEX_IDLE_MS) {
    this.app = app;
    this.getClient = getClient;
    this.idleMs = idleMs;
    this.changedPaths = /* @__PURE__ */ new Set();
    this.idleTimer = null;
    this.eventRefs = [];
  }
  attach(registerEvent) {
    const markChanged = (path3) => {
      if (!shouldIndex(path3)) return;
      this.changedPaths.add(path3);
      this.resetIdleTimer();
    };
    const track = (ref) => {
      this.eventRefs.push(ref);
      registerEvent(ref);
    };
    track(
      this.app.vault.on("create", (file) => {
        if (file instanceof import_obsidian9.TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("modify", (file) => {
        if (file instanceof import_obsidian9.TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("delete", (file) => {
        if (file instanceof import_obsidian9.TFile) markChanged(file.path);
      })
    );
    track(
      this.app.vault.on("rename", (file, oldPath) => {
        if (oldPath && shouldIndex(oldPath)) markChanged(oldPath);
        if (file instanceof import_obsidian9.TFile) markChanged(file.path);
      })
    );
  }
  detach() {
    this.clearIdleTimer();
    this.changedPaths.clear();
    this.eventRefs = [];
  }
  resetIdleTimer() {
    this.clearIdleTimer();
    this.idleTimer = window.setTimeout(() => void this.flush(), this.idleMs);
  }
  clearIdleTimer() {
    if (this.idleTimer !== null) {
      window.clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
  }
  async flush() {
    this.idleTimer = null;
    if (this.changedPaths.size === 0) return;
    const paths = [...this.changedPaths];
    this.changedPaths.clear();
    const client = this.getClient();
    if (!client) {
      for (const path3 of paths) this.changedPaths.add(path3);
      this.resetIdleTimer();
      return;
    }
    const results = await Promise.allSettled(paths.map((path3) => client.indexFile(path3)));
    for (let i = 0; i < results.length; i++) {
      const result = results[i];
      if (result.status === "rejected") {
        console.warn("[obsidian-context-mcp] auto-index failed:", paths[i], result.reason);
        this.changedPaths.add(paths[i]);
      }
    }
    if (this.changedPaths.size > 0) {
      this.resetIdleTimer();
    }
  }
};

// src/main.ts
var ObsidianContextPlugin = class extends import_obsidian10.Plugin {
  constructor() {
    super(...arguments);
    this.settings = DEFAULT_SETTINGS;
    this.sidecar = null;
    this.client = null;
    this.runtime = null;
    this.startPromise = null;
    this.settingTab = null;
    this.vaultAutoIndexer = null;
    this.llmRibbonEl = null;
    this.statusText = "Not started";
  }
  async onload() {
    try {
      await this.loadSettings();
      this.settingTab = new ObsidianContextSettingTab(this.app, this);
      this.addSettingTab(this.settingTab);
      const pluginDir = resolvePluginDir(this.app, this.manifest);
      const dataDir = resolvePluginDataDir(this.app, this.manifest);
      const vaultPath = this.getVaultPath();
      if (!vaultPath) {
        this.statusText = "\u041D\u0443\u0436\u0435\u043D \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault (\u043D\u0435 \u043E\u0431\u043B\u0430\u0447\u043D\u044B\u0439 \u0431\u0435\u0437 basePath)";
        new import_obsidian10.Notice("Obsidian Context MCP: \u043E\u0442\u043A\u0440\u043E\u0439 \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u044B\u0439 vault \u0438\u043B\u0438 \u0443\u043A\u0430\u0436\u0438 Python command \u0432 \u043D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0430\u0445.");
        return;
      }
      this.sidecar = new SidecarManager(
        vaultPath,
        pluginDir,
        dataDir,
        this.settings.pythonCommand,
        this.settings.serverPort
      );
      this.addCommand({
        id: "ocm-semantic-search",
        name: "Semantic search vault",
        callback: () => void this.openSearchModal()
      });
      this.addCommand({
        id: "ocm-llm-search",
        name: "Ask vault (LLM)",
        callback: () => void this.openLlmSearchModal()
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
      this.addRibbonIcon("scan-search", "\u0421\u0435\u043C\u0430\u043D\u0442\u0438\u0447\u0435\u0441\u043A\u0438\u0439 \u043F\u043E\u0438\u0441\u043A vault", () => {
        void this.openSearchModal();
      });
      const statusItem = this.addStatusBarItem();
      statusItem.setText("OCM");
      (0, import_obsidian10.setTooltip)(statusItem, this.statusText);
      statusItem.onClickEvent(() => void this.openSearchModal());
      if (this.settings.autoStart) {
        window.setTimeout(() => {
          void this.startSidecar().catch((e) => new import_obsidian10.Notice(String(e)));
        }, 500);
      }
      this.setupVaultAutoIndex();
      this.refreshLlmRibbon();
    } catch (e) {
      console.error("[obsidian-context-mcp] onload failed:", e);
      this.statusText = `Plugin error: ${e}`;
      new import_obsidian10.Notice(`Obsidian Context MCP: \u043E\u0448\u0438\u0431\u043A\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438 \u2014 ${e}`);
    }
  }
  refreshSettingsDisplay() {
    this.settingTab?.display();
  }
  getRuntimePort() {
    return this.sidecar?.readRuntime()?.port ?? this.runtime?.port ?? null;
  }
  applyVaultStatus(status) {
    this.statusText = formatIndexStatus(
      status.fileCount,
      status.vaultFileCount ?? status.fileCount,
      status.indexStatus
    );
    this.refreshSettingsDisplay();
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
      this.settings.pythonCommand,
      this.settings.serverPort
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
    new import_obsidian10.Notice("vault-server \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0449\u0435\u043D");
  }
  async onunload() {
    this.vaultAutoIndexer?.detach();
    this.vaultAutoIndexer = null;
    this.llmRibbonEl = null;
    if (this.settings.stopServerOnQuit) {
      try {
        await this.sidecar?.forceStopForRestart();
      } catch (e) {
        console.error("[obsidian-context-mcp] stop on quit:", e);
      }
    }
    this.client = null;
    this.runtime = null;
    this.startPromise = null;
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  async startSidecar() {
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.startSidecarOnce().finally(() => {
      this.startPromise = null;
    });
    return this.startPromise;
  }
  async startSidecarOnce() {
    try {
      const sidecar = this.ensureSidecar();
      this.runtime = await sidecar.start();
      this.client = SidecarClient.fromRuntime(this.runtime);
      const status = await this.client.status();
      this.applyVaultStatus(status);
      void this.syncLlmModelReady();
    } catch (e) {
      const attached = await this.sidecar?.tryAttachRunning();
      if (attached) {
        this.runtime = attached;
        this.client = SidecarClient.fromRuntime(attached);
        const status = await this.client.status();
        this.applyVaultStatus(status);
        void this.syncLlmModelReady();
        return;
      }
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
  /** Public wrapper for settings UI. */
  ensureClientPublic() {
    return this.ensureClient();
  }
  async startSidecarPublic() {
    return this.startSidecar();
  }
  refreshLlmRibbon() {
    const show = isLlmUiEnabled(this.settings) && this.settings.llmModelReady;
    if (show && !this.llmRibbonEl) {
      this.llmRibbonEl = this.addRibbonIcon("message-circle", "\u0421\u043F\u0440\u043E\u0441\u0438\u0442\u044C vault (LLM)", () => {
        void this.openLlmSearchModal();
      });
    } else if (!show && this.llmRibbonEl) {
      this.llmRibbonEl.remove();
      this.llmRibbonEl = null;
    }
  }
  async openLlmSearchModal() {
    try {
      if (!this.client) await this.startSidecar();
      if (!this.settings.llmModelReady) {
        new import_obsidian10.Notice("\u0421\u043D\u0430\u0447\u0430\u043B\u0430 \u0441\u043A\u0430\u0447\u0430\u0439\u0442\u0435 \u043C\u043E\u0434\u0435\u043B\u044C \u0432 Settings \u2192 Vault LLM");
        return;
      }
      new LlmSearchModal(this.app, this, this.ensureClient()).open();
    } catch (e) {
      new import_obsidian10.Notice(String(e));
      throw e;
    }
  }
  async openSearchModal() {
    try {
      if (!this.client) await this.startSidecar();
      new SearchModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new import_obsidian10.Notice(String(e));
      throw e;
    }
  }
  async openScopesModal() {
    try {
      if (!this.client) await this.startSidecar();
      new ScopesModal(this.app, this.ensureClient()).open();
    } catch (e) {
      new import_obsidian10.Notice(String(e));
      throw e;
    }
  }
  setupVaultAutoIndex() {
    if (!this.settings.autoReindexOnChange) return;
    this.vaultAutoIndexer?.detach();
    this.vaultAutoIndexer = new VaultAutoIndexer(this.app, () => this.client);
    this.vaultAutoIndexer.attach((ref) => this.registerEvent(ref));
  }
  async syncLlmModelReady() {
    const cfg = getActiveLlmConfig(this.settings);
    if (!cfg || !this.client) return;
    try {
      const status = await this.client.llmStatus(cfg.host, cfg.model, cfg.backend);
      if (status.modelAvailable !== this.settings.llmModelReady) {
        this.settings.llmModelReady = status.modelAvailable;
        await this.saveSettings();
        this.refreshLlmRibbon();
        this.refreshSettingsDisplay();
      }
    } catch {
    }
  }
  async reindexVault() {
    try {
      if (!this.client) await this.startSidecar();
      const client = this.ensureClient();
      await client.reindex("incremental");
      await watchReindexProgress(() => client.indexJobStatus());
      const status = await client.status();
      this.applyVaultStatus(status);
    } catch (e) {
      new import_obsidian10.Notice(String(e));
      throw e;
    }
  }
};
