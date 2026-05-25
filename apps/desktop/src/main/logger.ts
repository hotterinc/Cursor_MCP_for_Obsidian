import { appendFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'

export function getLogPath(): string {
  const dir = join(app.getPath('userData'), 'logs')
  mkdirSync(dir, { recursive: true })
  return join(dir, 'desktop.log')
}

export function log(message: string): void {
  const line = `[${new Date().toISOString()}] ${message}\n`
  appendFileSync(getLogPath(), line, 'utf-8')
}
