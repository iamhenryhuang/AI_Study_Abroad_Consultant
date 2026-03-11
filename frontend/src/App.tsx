import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Chat } from './components/Chat'

import { Sidebar } from './components/Sidebar'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen overflow-hidden bg-mesh font-sans text-gray-800">
        <Sidebar />
        <Chat />
      </div>
    </QueryClientProvider>
  )
}
