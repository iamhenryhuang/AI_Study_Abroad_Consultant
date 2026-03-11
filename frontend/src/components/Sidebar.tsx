import { Plus, MessageSquare, Settings, User } from 'lucide-react'

export function Sidebar() {
  return (
    <div className="w-64 h-screen bg-[#1e1e24] text-gray-300 flex flex-col pt-6 pb-4 px-3 shrink-0 absolute md:static z-40 transition-transform -translate-x-full md:translate-x-0">
      
      {/* New Chat Button */}
      <button className="flex items-center gap-2 w-full bg-[#2d2d34] hover:bg-[#36363e] text-white px-4 py-3 rounded-xl transition-colors font-medium border border-gray-700/50 mb-6">
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      {/* Chat History Placeholder */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-2 custom-scrollbar">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 mb-3">Recent</p>
        
        <button className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg hover:bg-[#2d2d34] transition-colors group">
          <MessageSquare size={16} className="text-gray-500 group-hover:text-gray-300 shrink-0" />
          <span className="text-sm truncate">CMU admission requirements</span>
        </button>
        
        <button className="flex items-center gap-3 w-full text-left px-3 py-2.5 rounded-lg hover:bg-[#2d2d34] transition-colors group">
          <MessageSquare size={16} className="text-gray-500 group-hover:text-gray-300 shrink-0" />
          <span className="text-sm truncate">Compare Stanford vs MIT</span>
        </button>
      </div>

      {/* Footer Settings */}
      <div className="mt-auto pt-4 border-t border-gray-800 space-y-1">
        <button className="flex items-center gap-3 w-full text-left px-3 py-2 rounded-lg hover:bg-[#2d2d34] transition-colors">
          <Settings size={18} className="text-gray-400" />
          <span className="text-sm">Settings</span>
        </button>
        <button className="flex items-center gap-3 w-full text-left px-3 py-2 rounded-lg hover:bg-[#2d2d34] transition-colors">
          <User size={18} className="text-gray-400" />
          <span className="text-sm">User Profile</span>
        </button>
      </div>
    </div>
  )
}
