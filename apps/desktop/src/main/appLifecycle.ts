import { app, BrowserWindow } from 'electron'
import { readFileSync, existsSync } from 'fs'
import { getOpenRequestPath } from './deepLink'
import { setProjectRoot, getProjectRoot } from './ipc'
import { sidecar } from './pythonSidecar'
import { log } from './logger'

export function setupSingleInstance(mainWindow: BrowserWindow): void {
  const gotLock = app.requestSingleInstanceLock()
  if (!gotLock) {
    app.quit()
    return
  }

  app.on('second-instance', async (_event, argv) => {
    const rootFlag = argv.findIndex((a) => a === '--project-root')
    if (rootFlag >= 0 && argv[rootFlag + 1]) {
      setProjectRoot(argv[rootFlag + 1])
    }
    checkOpenRequest()
    const root = getProjectRoot()
    if (root) {
      try {
        await sidecar.start(root)
      } catch (e) {
        log(`Failed to restart sidecar: ${e}`)
      }
    }
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.focus()
  })
}

export function checkOpenRequest(): void {
  const path = getOpenRequestPath()
  if (!existsSync(path)) return
  try {
    const data = JSON.parse(readFileSync(path, 'utf-8')) as { projectRoot?: string }
    if (data.projectRoot) setProjectRoot(data.projectRoot)
  } catch (e) {
    log(`Failed to read open request: ${e}`)
  }
}

export function parseCliProjectRoot(argv: string[]): string | null {
  const idx = argv.findIndex((a) => a === '--project-root')
  if (idx >= 0 && argv[idx + 1]) return argv[idx + 1]
  return null
}
