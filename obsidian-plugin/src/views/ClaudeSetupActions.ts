const { shell } = require("electron") as { shell: { openPath(path: string): Promise<string> } };
import { existsSync } from "fs";
import { dirname } from "path";

/** Open the Claude Desktop config file, or its folder when the file does not exist yet. */
export async function openClaudeDesktopConfig(configPath: string): Promise<string> {
  if (existsSync(configPath)) return shell.openPath(configPath);
  const folder = dirname(configPath);
  if (existsSync(folder)) return shell.openPath(folder);
  return `Claude Desktop не найден: нет папки ${folder}`;
}
