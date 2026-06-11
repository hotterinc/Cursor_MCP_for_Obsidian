import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import * as fs from "fs";
import * as path from "path";
import type { VaultRuntimeInfo } from "../types";

export class SidecarManager {
  private process: ChildProcessWithoutNullStreams | null = null;
  private dataDir: string;
  private vaultPath: string;
  private pythonCommand: string;

  constructor(vaultPath: string, dataDir: string, pythonCommand: string) {
    this.vaultPath = vaultPath;
    this.dataDir = dataDir;
    this.pythonCommand = pythonCommand;
  }

  get runtimePath(): string {
    return path.join(this.dataDir, "runtime.json");
  }

  async start(): Promise<VaultRuntimeInfo> {
    if (this.process) {
      const existing = this.readRuntime();
      if (existing) return existing;
    }

    const bundled = path.join(
      path.dirname(this.dataDir),
      "bin",
      process.platform === "win32" ? "obsidian-context-mcp.exe" : "obsidian-context-mcp"
    );
    const command = fs.existsSync(bundled) ? bundled : this.pythonCommand;

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

    this.process.stdout.on("data", (d) => console.log("[vault-server]", d.toString()));
    this.process.stderr.on("data", (d) => console.error("[vault-server]", d.toString()));
    this.process.on("exit", () => {
      this.process = null;
    });

    return this.waitForRuntime(30000);
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill("SIGTERM");
      this.process = null;
    }
    if (fs.existsSync(this.runtimePath)) {
      fs.unlinkSync(this.runtimePath);
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
