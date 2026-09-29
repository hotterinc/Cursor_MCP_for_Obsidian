import { spawn } from "child_process";
const { shell } = require("electron") as { shell: { openPath(path: string): Promise<string> } };
import { existsSync } from "fs";
import { homedir, platform } from "os";
import { join } from "path";

export async function openCodexConfig(): Promise<string> {
  const directory = join(homedir(), ".codex");
  const config = join(directory, "config.toml");
  return shell.openPath(existsSync(config) ? config : directory);
}

export function openEnvironmentVariables(onError: (error: Error) => void): void {
  if (platform() !== "win32") throw new Error("Available only on Windows");
  const child = spawn("rundll32.exe", ["sysdm.cpl,EditEnvironmentVariables"], {
    detached: true,
    stdio: "ignore",
    windowsHide: false,
  });
  child.on("error", onError);
  child.unref();
}
