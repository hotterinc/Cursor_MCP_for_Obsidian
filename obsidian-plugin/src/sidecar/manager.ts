import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import * as fs from "fs";
import * as path from "path";
import { requestUrl } from "obsidian";
import { resolveSidecarCommand } from "../paths";
import type { VaultRuntimeInfo } from "../types";

async function healthCheck(url: string, timeoutMs: number): Promise<boolean> {
  try {
    const res = await Promise.race([
      requestUrl({ url, method: "GET", throw: false }),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("timeout")), timeoutMs)
      ),
    ]);
    return res.status >= 200 && res.status < 300;
  } catch {
    return false;
  }
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

export class SidecarManager {
  private process: ChildProcessWithoutNullStreams | null = null;
  private ownsProcess = false;
  private dataDir: string;
  private vaultPath: string;
  private pluginDir: string;
  private pythonCommand: string;

  constructor(
    vaultPath: string,
    pluginDir: string,
    dataDir: string,
    pythonCommand: string
  ) {
    this.vaultPath = vaultPath;
    this.pluginDir = path.resolve(pluginDir);
    this.dataDir = path.resolve(dataDir);
    this.pythonCommand = pythonCommand;
    fs.mkdirSync(this.dataDir, { recursive: true });
  }

  get runtimePath(): string {
    return path.join(this.dataDir, "runtime.json");
  }

  private get lockPath(): string {
    return path.join(this.dataDir, "locks", "vault-server.lock");
  }

  /** Stop our process and any orphaned vault-server for this vault (user-initiated restart). */
  async forceStopForRestart(): Promise<void> {
    await this.stop();

    if (fs.existsSync(this.lockPath)) {
      try {
        const pid = Number.parseInt(fs.readFileSync(this.lockPath, "utf-8").trim(), 10);
        if (isPidAlive(pid)) {
          process.kill(pid, "SIGTERM");
          await new Promise((r) => setTimeout(r, 750));
        }
      } catch {
        /* ignore */
      }
      try {
        fs.unlinkSync(this.lockPath);
      } catch {
        /* ignore */
      }
    }

    if (fs.existsSync(this.runtimePath)) {
      try {
        fs.unlinkSync(this.runtimePath);
      } catch {
        /* ignore */
      }
    }
  }

  private async isHealthy(runtime: VaultRuntimeInfo): Promise<boolean> {
    return healthCheck(`http://${runtime.host}:${runtime.port}/health`, 2000);
  }

  async start(): Promise<VaultRuntimeInfo> {
    const existing = this.readRuntime();
    if (existing && (await this.isHealthy(existing))) {
      this.ownsProcess = false;
      return existing;
    }

    return new Promise((resolve, reject) => {
      let settled = false;
      const fail = (err: Error) => {
        if (settled) return;
        settled = true;
        reject(err);
      };

      const command = resolveSidecarCommand(this.pluginDir, this.pythonCommand);

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
            "0",
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
        fail(new Error(`Не удалось запустить vault-server (${command}): ${err.message}`));
      });

      this.process.stdout?.on("data", (d) => console.log("[vault-server]", d.toString()));
      this.process.stderr?.on("data", (d) => console.error("[vault-server]", d.toString()));
      this.process.on("exit", (code) => {
        console.error(`[vault-server] exited with code ${code}`);
        this.process = null;
        this.ownsProcess = false;
        if (fs.existsSync(this.runtimePath)) {
          try {
            fs.unlinkSync(this.runtimePath);
          } catch {
            /* ignore */
          }
        }
        if (!settled) {
          fail(
            new Error(
              code === 1
                ? "vault-server уже запущен или lock занят. Нажмите Restart server."
                : `vault-server завершился с кодом ${code}. См. data/logs/vault-server.log`
            )
          );
        }
      });

      this.waitForRuntime(30000)
        .then((runtime) => {
          if (settled) return;
          settled = true;
          resolve(runtime);
        })
        .catch(fail);
    });
  }

  async stop(): Promise<void> {
    // Only stop a process we spawned; never kill an external vault-server.
    if (this.process && this.ownsProcess) {
      this.process.kill("SIGTERM");
      this.process = null;
      this.ownsProcess = false;
      if (fs.existsSync(this.runtimePath)) {
        try {
          fs.unlinkSync(this.runtimePath);
        } catch {
          /* ignore */
        }
      }
    }
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
      };
    } catch {
      return null;
    }
  }

  private waitForRuntime(timeoutMs: number): Promise<VaultRuntimeInfo> {
    const started = Date.now();
    return new Promise((resolve, reject) => {
      const tick = () => {
        const runtime = this.readRuntime();
        if (runtime?.port) {
          resolve(runtime);
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
}
