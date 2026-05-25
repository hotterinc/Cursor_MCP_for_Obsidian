import { app, BrowserWindow } from 'electron'
import { createMainWindow } from './window'
import { registerIpcHandlers, setProjectRoot, getProjectRoot } from './ipc'
import { createTray } from './tray'
import { checkOpenRequest, parseCliProjectRoot, setupSingleInstance } from './appLifecycle'
import { readLastActiveProjectRoot } from './deepLink'
import { sidecar } from './pythonSidecar'
import { log } from './logger'

async function bootstrapProjectRoot(): Promise<string | null> {
  const cliRoot = parseCliProjectRoot(process.argv)
  if (cliRoot) {
    setProjectRoot(cliRoot)
  } else {
    const last = readLastActiveProjectRoot()
    if (last) setProjectRoot(last)
  }
  checkOpenRequest()
  return getProjectRoot()
}

app.whenReady().then(async () => {
  registerIpcHandlers()
  const root = await bootstrapProjectRoot()

  const mainWindow = createMainWindow()
  setupSingleInstance(mainWindow)
  createTray(mainWindow)

  if (root) {
    try {
      await sidecar.start(root)
    } catch (e) {
      log(`Failed to start sidecar: ${e}`)
    }
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', async () => {
  await sidecar.stop()
})
