import { spawn, spawnSync, ChildProcess } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { requestUrl } from "obsidian";
import { resolveSidecarCommand } from "../paths";
import type { VaultRuntimeInfo } from "../types";

/** First PyInstaller cold start + embedding model load can exceed 30s. */
const SIDECAR_STARTUP_TIMEOUT_MS = 120_000;

async function healthCheck(url: string, timeoutMs: number, vaultId: string): Promise<boolean> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const res = await Promise.race([
      requestUrl({ url, method: "GET", throw: false }),
      new Promise<never>((_, reject) =>
        timer = setTimeout(() => reject(new Error("timeout")), timeoutMs)
      ),
    ]);
    return res.status >= 200 && res.status < 300 && res.json?.vaultId === vaultId;
  } catch {
    return false;
  } finally { if (timer) clearTimeout(timer); }
}

function isPidAlive(pid: number): boolean {
  if (!Number.isFinite(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function clearMacQuarantine(binaryPath: string): void {
  if (process.platform !== "darwin" || !fs.existsSync(binaryPath)) return;
  try {
    const probe = spawnSync("xattr", ["-p", "com.apple.quarantine", binaryPath], {
      encoding: "utf-8",
    });
    if (probe.status === 0) {
      spawnSync("xattr", ["-d", "com.apple.quarantine", binaryPath]);
    }
  } catch {
    /* ignore */
  }
}

function unlinkIfExists(filePath: string): void {
  try {
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  } catch {
    /* ignore */
  }
}

/** Runtime and lock PIDs are hints; verify the OS command before signalling. */
function ownsServerPid(pid: number, dataDir: string): boolean {
  try {
    const result = process.platform === "win32"
      ? spawnSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", `(Get-CimInstance Win32_Process -Filter 'ProcessId = ${pid}').CommandLine`], {encoding: "utf8", windowsHide: true})
      : spawnSync("ps", ["-p", String(pid), "-o", "args="], {encoding: "utf8"});
    const command = result.stdout?.replace(/\\/g, "/") ?? "";
    return result.status === 0 && command.includes("vault-server") && command.includes(dataDir.replace(/\\/g, "/"));
  } catch { return false; }
}

function logVaultServerLine(text: string, stream: "stdout" | "stderr"): void {
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const isError =
      stream === "stderr" &&
      /\b(ERROR|Error:|Traceback|Exception|failed)\b/.test(trimmed) &&
      !/^INFO:/.test(trimmed);
    if (isError) {
      console.error("[vault-server]", trimmed);
    } else {
      console.log("[vault-server]", trimmed);
    }
  }
}

export class SidecarManager {
  private process: ChildProcess | null = null;
  private ownsProcess = false;
  private startPromise: Promise<VaultRuntimeInfo> | null = null;
  private dataDir: string;
  private vaultPath: string;
  private pluginDir: string;
  private pythonCommand: string;
  private serverPort: number;

  constructor(
    vaultPath: string,
    pluginDir: string,
    dataDir: string,
    pythonCommand: string,
    serverPort: number
  ) {
    this.vaultPath = vaultPath;
    this.pluginDir = path.resolve(pluginDir);
    this.dataDir = path.resolve(dataDir);
    this.pythonCommand = pythonCommand;
    this.serverPort = serverPort;
    fs.mkdirSync(this.dataDir, { recursive: true });
  }

  get runtimePath(): string {
    return path.join(this.dataDir, "runtime.json");
  }

  private get lockPath(): string {
    return path.join(this.dataDir, "locks", "vault-server.lock");
  }

  private readLockPid(): number | null {
    if (!fs.existsSync(this.lockPath)) return null;
    try {
      const pid = Number.parseInt(fs.readFileSync(this.lockPath, "utf-8").trim(), 10);
      return Number.isFinite(pid) && pid > 0 ? pid : null;
    } catch {
      return null;
    }
  }

  private collectServerPids(): number[] {
    const pids = new Set<number>();
    const lockPid = this.readLockPid();
    if (lockPid) pids.add(lockPid);
    const runtime = this.readRuntime();
    if (runtime?.pid) pids.add(runtime.pid);
    if (this.process?.pid) pids.add(this.process.pid);

    return [...pids].filter(pid => pid === this.process?.pid || ownsServerPid(pid, this.dataDir));
  }

  private async terminatePid(pid: number, timeoutMs = 5000): Promise<void> {
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
      /* ignore */
    }
    await new Promise((r) => setTimeout(r, 300));
  }

  /** Stop every vault-server instance tied to this vault data dir. */
  async clearServerState(): Promise<void> {
    const candidates = [this.readLockPid(), this.readRuntime()?.pid].filter((pid): pid is number => !!pid && isPidAlive(pid));
    const owned = this.collectServerPids();
    if (candidates.some(pid => !owned.includes(pid))) {
      throw new Error("Cannot restart: runtime/lock refers to an unverified process. It was left running.");
    }
    for (const pid of owned) {
      await this.terminatePid(pid);
    }
    this.process = null;
    this.ownsProcess = false;
    unlinkIfExists(this.lockPath);
    unlinkIfExists(this.runtimePath);
  }

  async forceStopForRestart(): Promise<void> {
    this.startPromise = null;
    await this.clearServerState();
  }

  private async isHealthy(runtime: VaultRuntimeInfo): Promise<boolean> {
    if (!runtime.adminToken || !runtime.vault_id || runtime.host !== "127.0.0.1") return false;
    let config;
    try { config = JSON.parse(fs.readFileSync(path.join(this.dataDir, "vault.json"), "utf8")); } catch { return false; }
    if (path.resolve(config.vault_real_path ?? config.vault_path ?? "") !== fs.realpathSync(this.vaultPath)) return false;
    if (runtime.vault_id !== config.vault_id || (this.serverPort > 0 && runtime.port !== this.serverPort)) return false;
    return healthCheck(`http://${runtime.host}:${runtime.port}/health`, 2000, runtime.vault_id);
  }

  private async prepareForStart(): Promise<VaultRuntimeInfo | null> {
    const existing = this.readRuntime();
    if (existing && (await this.isHealthy(existing))) {
      this.ownsProcess = false;
      return existing;
    }

    const lockPid = this.readLockPid();
    const staleLock = lockPid !== null && isPidAlive(lockPid);
    const staleRuntime = existing !== null && !(await this.isHealthy(existing));

    if (staleLock || staleRuntime) {
      await this.clearServerState();
    } else {
      unlinkIfExists(this.lockPath);
      if (!existing) {
        unlinkIfExists(this.runtimePath);
      }
    }
    return null;
  }

  async start(): Promise<VaultRuntimeInfo> {
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.startOnce().finally(() => {
      this.startPromise = null;
    });
    return this.startPromise;
  }

  private async startOnce(): Promise<VaultRuntimeInfo> {
    const attached = await this.prepareForStart();
    if (attached) return attached;

    return new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err: Error) => {
        if (settled) return;
        settled = true;
        reject(err);
      };

      const command = resolveSidecarCommand(this.pluginDir, this.pythonCommand);
      clearMacQuarantine(command);

      try {
        this.process = spawn(
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
            String(this.serverPort),
          ],
          {
            stdio: ["ignore", "pipe", "pipe"],
            detached: true,
            windowsHide: true,
            env: {
              ...process.env,
              TOKENIZERS_PARALLELISM: "false",
              OMP_NUM_THREADS: "1",
            },
          }
        );
        this.process!.unref();
      } catch (err) {
        fail(err instanceof Error ? err : new Error(String(err)));
        return;
      }

      this.ownsProcess = true;

      this.process!.on("error", (err) => {
        console.error("[vault-server] spawn error:", err);
        this.process = null;
        this.ownsProcess = false;
        fail(new Error(`Не удалось запустить vault-server (${command}): ${err.message}`));
      });

      this.process!.stdout?.on("data", (d) => logVaultServerLine(d.toString(), "stdout"));
      this.process!.stderr?.on("data", (d) => logVaultServerLine(d.toString(), "stderr"));
      this.process!.on("exit", (code) => {
        this.process = null;
        this.ownsProcess = false;
        if (!settled) {
          console.error(`[vault-server] exited with code ${code}`);
          fail(
            new Error(
              code === 1
                ? "vault-server не смог захватить lock. Нажмите Restart server ещё раз."
                : `vault-server завершился с кодом ${code}. См. data/logs/vault-server.log`
            )
          );
        } else if (code !== 0) {
          console.warn(`[vault-server] exited with code ${code}`);
        }
      });

      this.waitForHealthyRuntime(SIDECAR_STARTUP_TIMEOUT_MS, () => settled)
        .then((runtime) => {
          if (settled) return;
          settled = true;
          resolve(runtime);
        })
        .catch(fail);
    });
  }

  async stop(): Promise<void> {
    await this.clearServerState();
  }

  readRuntime(): VaultRuntimeInfo | null {
    if (!fs.existsSync(this.runtimePath)) return null;
    try {
      const raw = JSON.parse(fs.readFileSync(this.runtimePath, "utf-8"));
      return {
        port: raw.port,
        pid: raw.pid,
        host: raw.host ?? "127.0.0.1",
        status: raw.status,
        startedAt: raw.started_at ?? raw.startedAt,
        vault_id: raw.vault_id ?? raw.vaultId,
        adminToken: raw.adminToken ?? raw.admin_token,
      };
    } catch {
      return null;
    }
  }

  /** Attach when server outlived the startup waiter (e.g. slow first launch). */
  async tryAttachRunning(): Promise<VaultRuntimeInfo | null> {
    const runtime = this.readRuntime();
    if (runtime?.port && (await this.isHealthy(runtime))) {
      this.ownsProcess = false;
      this.process = null;
      return runtime;
    }
    return null;
  }

  private waitForHealthyRuntime(timeoutMs: number, cancelled: () => boolean): Promise<VaultRuntimeInfo> {
    const started = Date.now();
    return new Promise((resolve, reject) => {
      const tick = () => {
        void (async () => {
          if (cancelled()) { reject(new Error("Startup cancelled")); return; }
          const runtime = this.readRuntime();
          if (runtime?.port && (await this.isHealthy(runtime))) {
            resolve(runtime);
            return;
          }
          if (Date.now() - started > timeoutMs) {
            const late = this.readRuntime();
            if (late?.port && (await this.isHealthy(late))) {
              resolve(late);
              return;
            }
            reject(
              new Error(
                "Timed out waiting for vault-server HTTP endpoint (первый запуск может занять до 2 мин)"
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
}
