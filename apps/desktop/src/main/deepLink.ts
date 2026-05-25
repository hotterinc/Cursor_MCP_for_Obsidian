import { homedir } from 'os'
import { join } from 'path'

export function getOpenRequestPath(): string {
  const base =
    process.platform === 'win32'
      ? join(process.env.APPDATA ?? homedir(), 'obsidian-context-mcp')
      : join(homedir(), '.local', 'share', 'obsidian-context-mcp')
  return join(base, 'runtime', 'open-request.json')
}
