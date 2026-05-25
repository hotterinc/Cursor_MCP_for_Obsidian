import { spawn, type ChildProcessWithoutNullStreams } from 'child_process'
import { EventEmitter } from 'events'
import { join } from 'path'
import { app } from 'electron'
import { getAppDataDir } from './deepLink'
import { log } from './logger'

type JsonRpcResponse = {
  jsonrpc: string
  id?: string | number | null
  result?: Record<string, unknown>
  error?: { code: number; message: string }
}

type PendingRequest = {
  resolve: (value: Record<string, unknown>) => void
  reject: (error: Error) => void
}

export class PythonSidecar extends EventEmitter {
  private proc: ChildProcessWithoutNullStreams | null = null
  private buffer = ''
  private requestId = 0
  private pending = new Map<number, PendingRequest>()
  private projectRoot: string | null = null

  async start(projectRoot: string): Promise<void> {
    if (this.proc && this.projectRoot === projectRoot) return
    await this.stop()
    this.projectRoot = projectRoot

    const isDev = !app.isPackaged
    const repoRoot = join(app.getAppPath(), '..', '..')
    const pythonDir = join(repoRoot, 'python')

    if (isDev) {
      this.proc = spawn(
        'python',
        ['-m', 'uv', '--directory', pythonDir, 'run', 'obsidian-context-mcp', 'gui-backend', '--project-root', projectRoot],
        {
          stdio: ['pipe', 'pipe', 'pipe'],
          env: {
            ...process.env,
            PYTHONUNBUFFERED: '1',
            OBSIDIAN_CONTEXT_DATA_DIR: getAppDataDir()
          }
        }
      )
    } else {
      const sidecar = join(process.resourcesPath, 'python-sidecar', 'obsidian-context-mcp')
      this.proc = spawn(sidecar, ['gui-backend', '--project-root', projectRoot], {
        stdio: ['pipe', 'pipe', 'pipe']
      })
    }

    this.proc.stdout.on('data', (chunk: Buffer) => this.handleStdout(chunk.toString()))
    this.proc.stderr.on('data', (chunk: Buffer) => log(`[python stderr] ${chunk.toString().trim()}`))
    this.proc.on('exit', (code) => {
      log(`Python sidecar exited with code ${code}`)
      this.proc = null
    })

    log(`Python sidecar started for ${projectRoot}`)
  }

  async stop(): Promise<void> {
    if (this.proc) {
      this.proc.kill()
      this.proc = null
    }
    this.pending.forEach((p) => p.reject(new Error('Sidecar stopped')))
    this.pending.clear()
  }

  private handleStdout(data: string): void {
    this.buffer += data
    const lines = this.buffer.split('\n')
    this.buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const msg = JSON.parse(line) as JsonRpcResponse & { method?: string; params?: Record<string, unknown> }
        if (msg.method) {
          this.emit('event', msg.method, msg.params ?? {})
          continue
        }
        if (msg.id !== undefined && msg.id !== null) {
          const pending = this.pending.get(Number(msg.id))
          if (pending) {
            this.pending.delete(Number(msg.id))
            if (msg.error) pending.reject(new Error(msg.error.message))
            else pending.resolve(msg.result ?? {})
          }
        }
      } catch {
        log(`Failed to parse JSON-RPC line: ${line}`)
      }
    }
  }

  call(method: string, params: Record<string, unknown> = {}): Promise<Record<string, unknown>> {
    return new Promise((resolve, reject) => {
      if (!this.proc?.stdin) {
        reject(new Error('Python sidecar not running'))
        return
      }
      const id = ++this.requestId
      this.pending.set(id, { resolve, reject })
      const payload = JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'
      this.proc.stdin.write(payload)
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error(`RPC timeout: ${method}`))
        }
      }, 30000)
    })
  }
}

export const sidecar = new PythonSidecar()
