import type { ObsidianContextApi } from '../../preload/index'

declare global {
  interface Window {
    obsidianContext: ObsidianContextApi
  }
}

export const api = window.obsidianContext
