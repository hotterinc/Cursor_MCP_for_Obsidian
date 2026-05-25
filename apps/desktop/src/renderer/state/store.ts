import { create } from 'zustand'
import type { ProjectStatus } from '../../preload/index'

interface AppState {
  project: ProjectStatus | null
  setProject: (p: ProjectStatus | null) => void
  indexProgress: Record<string, unknown> | null
  setIndexProgress: (p: Record<string, unknown> | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  project: null,
  setProject: (project) => set({ project }),
  indexProgress: null,
  setIndexProgress: (indexProgress) => set({ indexProgress })
}))
