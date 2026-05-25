import { app, BrowserWindow } from 'electron'
import { createMainWindow } from './window'
import { registerIpcHandlers, setProjectRoot } from './ipc'
import { createTray } from './tray'
import { checkOpenRequest, parseCliProjectRoot, setupSingleInstance } from './appLifecycle'
import { sidecar } from './pythonSidecar'
import { log } from './logger'

app.whenReady().then(async () => {
  registerIpcHandlers()
  const cliRoot = parseCliProjectRoot(process.argv)
  if (cliRoot) setProjectRoot(cliRoot)
  checkOpenRequest()

  const mainWindow = createMainWindow()
  setupSingleInstance(mainWindow)
  createTray(mainWindow)

  const root = cliRoot
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
