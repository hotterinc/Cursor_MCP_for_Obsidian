import { BrowserWindow, shell } from 'electron'
import { join } from 'path'

const DEFAULT_WIDTH = 1100
const DEFAULT_HEIGHT = 760
const MIN_WIDTH = 900
const MIN_HEIGHT = 620

export function createMainWindow(): BrowserWindow {
  const bounds = getSavedBounds()
  const win = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    x: bounds.x,
    y: bounds.y,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    show: false,
    title: 'Obsidian Context MCP',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      preload: join(__dirname, '../preload/index.js')
    }
  })

  win.on('ready-to-show', () => win.show())
  win.on('close', () => saveBounds(win))
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return win
}

function getSavedBounds() {
  return { width: DEFAULT_WIDTH, height: DEFAULT_HEIGHT, x: undefined as number | undefined, y: undefined as number | undefined }
}

function saveBounds(_win: BrowserWindow): void {
  // Bounds persistence can be extended with electron-store
}
