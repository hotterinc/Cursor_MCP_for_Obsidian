import { contextBridge, ipcRenderer } from 'electron'

export interface ProjectStatus {
  projectId?: string
  projectRoot?: string
  projectRealPath?: string
  projectName?: string
  configured?: boolean
  vaultPath?: string
  status?: string
  writeAccess?: boolean
}

const obsidianContext = {
  getCurrentProject: (): Promise<ProjectStatus> => ipcRenderer.invoke('obsidian:getCurrentProject'),
  chooseProjectRoot: (): Promise<ProjectStatus & { canceled?: boolean }> =>
    ipcRenderer.invoke('obsidian:chooseProjectRoot'),
  chooseVaultFolder: (projectRoot?: string) => ipcRenderer.invoke('obsidian:chooseVaultFolder', { projectRoot }),
  saveProjectConfig: (input: Record<string, unknown>) => ipcRenderer.invoke('obsidian:saveProjectConfig', input),
  getIndexStatus: (projectRoot?: string) => ipcRenderer.invoke('obsidian:getIndexStatus', { projectRoot }),
  startIndexing: (input: { projectRoot?: string; mode?: string }) => ipcRenderer.invoke('obsidian:startIndexing', input),
  cancelIndexing: (jobId: string) => ipcRenderer.invoke('obsidian:cancelIndexing', { jobId }),
  searchDocs: (input: Record<string, unknown>) => ipcRenderer.invoke('obsidian:searchDocs', input),
  readNote: (input: Record<string, unknown>) => ipcRenderer.invoke('obsidian:readNote', input),
  listNotes: (input?: Record<string, unknown>) => ipcRenderer.invoke('obsidian:listNotes', input),
  runDiagnostics: (projectRoot?: string) => ipcRenderer.invoke('obsidian:runDiagnostics', { projectRoot }),
  openVaultFolder: (projectRoot?: string) => ipcRenderer.invoke('obsidian:openVaultFolder', { projectRoot }),
  openAppDataFolder: (projectRoot?: string) => ipcRenderer.invoke('obsidian:openAppDataFolder', { projectRoot }),
  openNoteInExternalApp: (input: Record<string, unknown>) => ipcRenderer.invoke('obsidian:openNoteInExternalApp', input),
  getSettings: (projectRoot?: string) => ipcRenderer.invoke('obsidian:getSettings', { projectRoot }),
  updateSettings: (input: Record<string, unknown>) => ipcRenderer.invoke('obsidian:updateSettings', input)
}

contextBridge.exposeInMainWorld('obsidianContext', obsidianContext)

export type ObsidianContextApi = typeof obsidianContext
