import { Link } from 'react-router-dom'
import { useAppStore } from '@/state/store'

export function VaultGate({ children }: { children: React.ReactNode }) {
  const project = useAppStore((s) => s.project)

  if (!project?.projectRoot) {
    return (
      <SetupHint
        title="Project not selected"
        message="Choose a Cursor project root on the Project page first."
        link="/"
        linkLabel="Open Project"
      />
    )
  }

  if (!project?.configured) {
    return (
      <SetupHint
        title="Obsidian vault not configured"
        message="Pick the folder with your .md notes (Obsidian vault or docs folder), then save."
        link="/vault"
        linkLabel="Vault Setup"
      />
    )
  }

  return <>{children}</>
}

function SetupHint({
  title,
  message,
  link,
  linkLabel
}: {
  title: string
  message: string
  link: string
  linkLabel: string
}) {
  return (
    <div className="max-w-lg space-y-3 rounded border border-yellow-700/50 bg-yellow-950/30 p-4 text-sm">
      <h2 className="font-semibold text-yellow-200">{title}</h2>
      <p className="text-slate-300">{message}</p>
      <Link
        to={link}
        className="inline-block px-3 py-1.5 rounded bg-[hsl(var(--primary))] text-white text-sm"
      >
        {linkLabel}
      </Link>
    </div>
  )
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded border border-red-700/50 bg-red-950/30 p-3 text-sm text-red-200">{message}</div>
  )
}

export function formatIpcError(err: unknown): string {
  if (err instanceof Error) return err.message
  return String(err)
}
