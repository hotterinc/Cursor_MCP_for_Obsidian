import type { BrowserWindow } from 'electron'
import { sidecar } from './pythonSidecar'

let attached = false

export function setupSidecarBroadcast(mainWindow: BrowserWindow): void {
  if (attached) return
  attached = true

  sidecar.on('event', (method: string, params: Record<string, unknown>) => {
    if (mainWindow.isDestroyed()) return
    mainWindow.webContents.send('obsidian:sidecar-event', { method, params })
  })

  sidecar.on('log', (line: string) => {
    if (mainWindow.isDestroyed()) return
    mainWindow.webContents.send('obsidian:sidecar-log', line)
  })
}
