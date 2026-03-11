import { useState } from 'react'
import { ChevronRight, Database, Search, FolderSearch, CheckCircle2 } from 'lucide-react'
import type { AgentEvent } from '../types'

const TOOL_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  search_general: { label: '全庫向量檢索', icon: Database },
  search_school: { label: '特定學校深度檢索', icon: Search },
  search_page_type: { label: '分類頁面過濾', icon: FolderSearch },
}

interface Props {
  events: AgentEvent[]
}

export function AgentSteps({ events }: Props) {
  const [open, setOpen] = useState(false)

  const toolCalls = events.filter(e => e.type === 'tool_call')
  const hasSteps = events.some(e => e.type === 'tool_call' || e.type === 'thinking')
  if (!hasSteps) return null

  return (
    <div className="mb-4 mt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-gray-800 transition-colors group cursor-pointer bg-white/50 backdrop-blur-sm px-3 py-1.5 rounded-full border border-gray-200/50 shadow-sm"
      >
        <div className={`p-0.5 rounded-full bg-gray-100 group-hover:bg-gray-200 transition-colors ${open ? 'rotate-90' : ''}`}>
          <ChevronRight size={12} strokeWidth={3} />
        </div>
        <span>AI 思考過程（執行 {toolCalls.length} 次工具）</span>
      </button>

      {open && (
        <div className="mt-3 ml-4 space-y-0 text-sm relative before:absolute before:inset-y-2 before:-left-[11px] before:w-px before:bg-gray-200">
          {events.map((event, i) => {
            if (event.type === 'thinking') {
              return (
                <div key={i} className="flex gap-4 items-start py-2">
                  <div className="relative z-10 w-2 h-2 rounded-full bg-gray-300 mt-1.5 shadow-[0_0_0_4px_white]" />
                  <div className="text-gray-400 italic text-xs">第 {event.step} 輪邏輯推演中...</div>
                </div>
              )
            }

            if (event.type === 'tool_call') {
              const toolInfo = TOOL_LABELS[event.tool] || { label: event.tool, icon: Search }
              const Icon = toolInfo.icon

              return (
                <div key={i} className="flex gap-4 items-start py-2 animate-slide-down">
                  <div className="relative z-10 w-[18px] h-[18px] rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center -ml-[4px] shadow-[0_0_0_4px_white]">
                     <Icon size={10} strokeWidth={3} />
                  </div>
                  <div className="flex-1 bg-white border border-gray-100 rounded-xl p-3 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-gray-700 text-xs">{toolInfo.label}</span>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                      {event.args.query && (
                        <span className="text-gray-500 text-xs bg-gray-50 px-2 py-1 rounded truncate max-w-[200px]" title={event.args.query}>
                          "{event.args.query}"
                        </span>
                      )}
                      {event.args.school_id && (
                        <span className="bg-indigo-50 text-indigo-600 px-2 py-1 rounded text-[10px] tracking-wide font-medium">
                          {event.args.school_id.toUpperCase()}
                        </span>
                      )}
                      {event.args.page_type && (
                        <span className="bg-emerald-50 text-emerald-600 px-2 py-1 rounded text-[10px] tracking-wide font-medium">
                          {event.args.page_type}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            }

            if (event.type === 'tool_result') {
              return (
                <div key={i} className="flex gap-4 items-start py-1">
                  <div className="relative z-10 w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shadow-[0_0_0_4px_white]" />
                  <div className="text-emerald-600 text-xs flex items-center gap-1">
                    <CheckCircle2 size={12} className="shrink-0" />
                    <span>檢索成功，找到相關文獻</span>
                  </div>
                </div>
              )
            }

            return null
          })}
        </div>
      )}
    </div>
  )
}
