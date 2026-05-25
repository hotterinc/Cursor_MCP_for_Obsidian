import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HashRouter } from 'react-router-dom'
import { Sidebar, StatusBar } from '@/components/Layout'
import { AppRoutes } from '@/routes'

const queryClient = new QueryClient()

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <div className="flex h-screen flex-col">
          <StatusBar />
          <div className="flex flex-1 overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-auto p-4">{<AppRoutes />}</main>
          </div>
        </div>
      </HashRouter>
    </QueryClientProvider>
  )
}
