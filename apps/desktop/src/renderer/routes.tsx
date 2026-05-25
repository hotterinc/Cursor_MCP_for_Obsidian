import { Routes, Route } from 'react-router-dom'
import { ProjectPage } from '@/pages/ProjectPage'
import { VaultSetupPage } from '@/pages/VaultSetupPage'
import { IndexingPage } from '@/pages/IndexingPage'
import { SearchPage } from '@/pages/SearchPage'
import { NotesPage } from '@/pages/NotesPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { DiagnosticsPage } from '@/pages/DiagnosticsPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<ProjectPage />} />
      <Route path="/vault" element={<VaultSetupPage />} />
      <Route path="/indexing" element={<IndexingPage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/notes" element={<NotesPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/diagnostics" element={<DiagnosticsPage />} />
    </Routes>
  )
}
