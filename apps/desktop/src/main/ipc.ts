import { z } from 'zod'
import { dialog, ipcMain, shell } from 'electron'
import { homedir } from 'os'
import { sidecar } from './pythonSidecar'
import { log } from './logger'

const projectRootSchema = z.object({ projectRoot: z.string().optional() }).optional()

const saveConfigSchema = z.object({
  projectRoot: z.string(),
  vaultPath: z.string(),
  writeAccess: z.boolean().optional(),
  backupBeforeEdit: z.boolean().optional(),
  include: z.array(z.string()).optional(),
  exclude: z.array(z.string()).optional()
})

const searchSchema = z.object({
  projectRoot: z.string().optional(),
  query: z.string(),
  mode: z.enum(['hybrid', 'semantic', 'lexical']).optional(),
  topK: z.number().optional()
})

const readNoteSchema = z.object({
  projectRoot: z.string().optional(),
  relativePath: z.string()
})

const indexStartSchema = z.object({
  projectRoot: z.string().optional(),
  mode: z.enum(['incremental', 'full']).optional()
})

const settingsUpdateSchema = z.object({
  projectRoot: z.string().optional(),
  writeAccess: z.boolean().optional(),
  backupBeforeEdit: z.boolean().optional(),
  watcherEnabled: z.boolean().optional(),
  embeddingProvider: z.string().optional(),
  embeddingModel: z.string().optional(),
  include: z.array(z.string()).optional(),
  exclude: z.array(z.string()).optional()
})

let currentProjectRoot: string | null = null

export async function ensureSidecar(projectRoot?: string): Promise<void> {
  const root = projectRoot ?? currentProjectRoot
  if (!root) throw new Error('No project root configured')
  await sidecar.start(root)
}

export function registerIpcHandlers(): void {
  ipcMain.handle('obsidian:getCurrentProject', async () => {
    if (!currentProjectRoot) {
      return { configured: false, status: 'not_configured' }
    }
    await ensureSidecar()
    return sidecar.call('project.getCurrent', { project_root: currentProjectRoot })
  })

  ipcMain.handle('obsidian:chooseProjectRoot', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: 'Choose Cursor project root',
      defaultPath: homedir()
    })
    if (result.canceled || !result.filePaths[0]) return { canceled: true }
    currentProjectRoot = result.filePaths[0]
    await sidecar.start(currentProjectRoot)
    return sidecar.call('project.setRoot', { project_root: currentProjectRoot })
  })

  ipcMain.handle('obsidian:chooseVaultFolder', async (_e, input?: { projectRoot?: string }) => {
    const parsed = projectRootSchema.parse(input)
    const root = parsed?.projectRoot ?? currentProjectRoot
    if (root) currentProjectRoot = root
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory'],
      title: 'Choose Obsidian documentation folder',
      defaultPath: homedir()
    })
    if (result.canceled || !result.filePaths[0]) return { canceled: true }
    await ensureSidecar(root ?? undefined)
    const validated = await sidecar.call('vault.validatePath', { vault_path: result.filePaths[0] })
    return validated
  })

  ipcMain.handle('obsidian:saveProjectConfig', async (_e, input: unknown) => {
    const data = saveConfigSchema.parse(input)
    currentProjectRoot = data.projectRoot
    await ensureSidecar()
    return sidecar.call('vault.saveConfig', {
      project_root: data.projectRoot,
      vault_path: data.vaultPath,
      write_access: data.writeAccess,
      backup_before_edit: data.backupBeforeEdit,
      include: data.include,
      exclude: data.exclude
    })
  })

  ipcMain.handle('obsidian:getIndexStatus', async (_e, input?: { projectRoot?: string }) => {
    await ensureSidecar(input?.projectRoot)
    return sidecar.call('index.status', { project_root: input?.projectRoot ?? currentProjectRoot })
  })

  ipcMain.handle('obsidian:startIndexing', async (_e, input: unknown) => {
    const data = indexStartSchema.parse(input)
    await ensureSidecar(data.projectRoot)
    return sidecar.call('index.start', {
      project_root: data.projectRoot ?? currentProjectRoot,
      mode: data.mode ?? 'incremental'
    })
  })

  ipcMain.handle('obsidian:cancelIndexing', async (_e, input: { jobId: string }) => {
    await ensureSidecar()
    return sidecar.call('index.cancel', { job_id: input.jobId })
  })

  ipcMain.handle('obsidian:searchDocs', async (_e, input: unknown) => {
    const data = searchSchema.parse(input)
    await ensureSidecar(data.projectRoot)
    return sidecar.call('search.docs', {
      project_root: data.projectRoot ?? currentProjectRoot,
      query: data.query,
      mode: data.mode ?? 'hybrid',
      top_k: data.topK ?? 10
    })
  })

  ipcMain.handle('obsidian:readNote', async (_e, input: unknown) => {
    const data = readNoteSchema.parse(input)
    await ensureSidecar(data.projectRoot)
    return sidecar.call('notes.read', {
      project_root: data.projectRoot ?? currentProjectRoot,
      relative_path: data.relativePath
    })
  })

  ipcMain.handle('obsidian:listNotes', async (_e, input?: { projectRoot?: string; query?: string; tag?: string; limit?: number }) => {
    await ensureSidecar(input?.projectRoot)
    return sidecar.call('notes.list', {
      project_root: input?.projectRoot ?? currentProjectRoot,
      query: input?.query,
      tag: input?.tag,
      limit: input?.limit ?? 50
    })
  })

  ipcMain.handle('obsidian:runDiagnostics', async (_e, input?: { projectRoot?: string }) => {
    await ensureSidecar(input?.projectRoot)
    return sidecar.call('diagnostics.run', { project_root: input?.projectRoot ?? currentProjectRoot })
  })

  ipcMain.handle('obsidian:openVaultFolder', async (_e, input?: { projectRoot?: string }) => {
    await ensureSidecar(input?.projectRoot)
    const req = await sidecar.call('app.openVaultPathRequest', {
      project_root: input?.projectRoot ?? currentProjectRoot
    })
    const path = String(req.absolutePath ?? '')
    if (path) await shell.openPath(path)
    return { ok: true }
  })

  ipcMain.handle('obsidian:openAppDataFolder', async (_e, input?: { projectRoot?: string }) => {
    await ensureSidecar(input?.projectRoot)
    const req = await sidecar.call('app.openAppDataPathRequest', {
      project_root: input?.projectRoot ?? currentProjectRoot
    })
    const path = String(req.absolutePath ?? '')
    if (path) await shell.openPath(path)
    return { ok: true }
  })

  ipcMain.handle('obsidian:openNoteInExternalApp', async (_e, input: { relativePath: string; projectRoot?: string }) => {
    await ensureSidecar(input.projectRoot)
    const note = await sidecar.call('notes.read', {
      project_root: input.projectRoot ?? currentProjectRoot,
      relative_path: input.relativePath
    })
    const vaultReq = await sidecar.call('app.openVaultPathRequest', {
      project_root: input.projectRoot ?? currentProjectRoot
    })
    const vaultPath = String(vaultReq.absolutePath ?? '')
    const fullPath = `${vaultPath}/${input.relativePath}`.replace(/\\/g, '/')
    await shell.openPath(fullPath)
    return { ok: true, note }
  })

  ipcMain.handle('obsidian:getSettings', async (_e, input?: { projectRoot?: string }) => {
    await ensureSidecar(input?.projectRoot)
    return sidecar.call('settings.get', { project_root: input?.projectRoot ?? currentProjectRoot })
  })

  ipcMain.handle('obsidian:updateSettings', async (_e, input: unknown) => {
    const data = settingsUpdateSchema.parse(input)
    await ensureSidecar(data.projectRoot)
    return sidecar.call('settings.update', {
      project_root: data.projectRoot ?? currentProjectRoot,
      write_access: data.writeAccess,
      backup_before_edit: data.backupBeforeEdit,
      watcher_enabled: data.watcherEnabled,
      embedding_provider: data.embeddingProvider,
      embedding_model: data.embeddingModel,
      include: data.include,
      exclude: data.exclude
    })
  })

  log('IPC handlers registered')
}

export function setProjectRoot(root: string): void {
  currentProjectRoot = root
}

export function getProjectRoot(): string | null {
  return currentProjectRoot
}
