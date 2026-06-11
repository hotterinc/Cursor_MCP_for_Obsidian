import * as fs from "fs";
import * as path from "path";
import type { App } from "obsidian";

/** Absolute path to plugin root (manifest.dir can be relative in Obsidian). */
export function resolvePluginDir(
  app: App,
  manifest: { dir: string; id: string }
): string {
  if (path.isAbsolute(manifest.dir)) {
    return manifest.dir;
  }
  const base = (app.vault.adapter as { basePath?: string }).basePath;
  if (!base) {
    throw new Error("Нужен локальный vault с basePath");
  }
  return path.join(base, ".obsidian", "plugins", manifest.id);
}

/** Absolute path to plugin data dir (manifest.dir can be relative in Obsidian). */
export function resolvePluginDataDir(
  app: App,
  manifest: { dir: string; id: string }
): string {
  return path.join(resolvePluginDir(app, manifest), "data");
}

export function bundledSidecarPath(pluginDir: string): string {
  const name =
    process.platform === "win32" ? "obsidian-context-mcp.exe" : "obsidian-context-mcp";
  return path.join(pluginDir, "bin", name);
}

/** Server candidates shipped inside the plugin folder (self-contained install). */
export function sidecarCandidates(pluginDir: string): string[] {
  if (process.platform === "win32") {
    return [
      bundledSidecarPath(pluginDir),
      path.join(pluginDir, "server", ".venv", "Scripts", "obsidian-context-mcp.exe"),
    ];
  }
  return [
    bundledSidecarPath(pluginDir),
    path.join(pluginDir, "server", ".venv", "bin", "obsidian-context-mcp"),
  ];
}

/** Prefer in-plugin server binary/venv; optional dev fallback via pythonCommand. */
export function resolveSidecarCommand(pluginDir: string, pythonCommand: string): string {
  for (const candidate of sidecarCandidates(pluginDir)) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return pythonCommand;
}

export function hasBundledSidecar(pluginDir: string): boolean {
  return sidecarCandidates(pluginDir).some((c) => fs.existsSync(c));
}

export function activeSidecarPath(pluginDir: string, pythonCommand: string): string | null {
  for (const candidate of sidecarCandidates(pluginDir)) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return pythonCommand.trim() || null;
}
