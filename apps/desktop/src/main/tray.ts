import { Menu, Tray, BrowserWindow, nativeImage } from 'electron'
import { getProjectRoot } from './ipc'
import { sidecar } from './pythonSidecar'

let tray: Tray | null = null

export function createTray(mainWindow: BrowserWindow): void {
  const icon = nativeImage.createEmpty()
  tray = new Tray(icon)
  tray.setToolTip('Obsidian Context MCP')
  updateTrayMenu(mainWindow)
  tray.on('click', () => mainWindow.show())
}

export function updateTrayMenu(mainWindow: BrowserWindow): void {
  if (!tray) return
  const projectName = getProjectRoot()?.split(/[/\\]/).pop() ?? 'None'
  const menu = Menu.buildFromTemplate([
    { label: 'Open Obsidian Context MCP', click: () => mainWindow.show() },
    { label: `Current project: ${projectName}`, enabled: false },
    { label: 'Index status: ready', enabled: false },
    { type: 'separator' },
    {
      label: 'Rebuild index',
      click: async () => {
        await sidecar.call('index.start', { mode: 'full' })
      }
    },
    {
      label: 'Open vault folder',
      click: async () => {
        const req = await sidecar.call('app.openVaultPathRequest', {})
        // handled via ipc in main
      }
    },
    { type: 'separator' },
    { label: 'Quit', click: () => mainWindow.close() }
  ])
  tray.setContextMenu(menu)
}
