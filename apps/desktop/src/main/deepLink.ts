import { existsSync, readFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'

const APP_NAME = 'obsidian-context-mcp'

/** Matches platformdirs.user_data_dir(APP_NAME) used by the Python core. */
export function getAppDataDir(): string {
  if (process.env.OBSIDIAN_CONTEXT_DATA_DIR) {
    return process.env.OBSIDIAN_CONTEXT_DATA_DIR
  }
  if (process.platform === 'win32') {
    return join(process.env.LOCALAPPDATA ?? homedir(), APP_NAME, APP_NAME)
  }
  if (process.platform === 'darwin') {
    return join(homedir(), 'Library', 'Application Support', APP_NAME)
  }
  return join(homedir(), '.local', 'share', APP_NAME)
}

export function getGlobalConfigPath(): string {
  return join(getAppDataDir(), 'config.json')
}

export function readLastActiveProjectRoot(): string | null {
  const path = getGlobalConfigPath()
  if (!existsSync(path)) return null
  try {
    const data = JSON.parse(readFileSync(path, 'utf-8')) as { lastActiveProjectRoot?: string }
    const root = data.lastActiveProjectRoot
    return root && existsSync(root) ? root : null
  } catch {
    return null
  }
}

export function getOpenRequestPath(): string {
  return join(getAppDataDir(), 'runtime', 'open-request.json')
}
