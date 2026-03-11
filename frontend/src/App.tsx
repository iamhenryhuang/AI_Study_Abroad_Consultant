import { useState, useEffect, useRef } from 'react'
import { Settings } from 'lucide-react'
import { useStreamChat } from './hooks/useStreamChat'
import { SettingsModal } from './components/SettingsModal'
import { ResumeUpload } from './components/ResumeUpload'
import { ChatInput } from './components/ChatInput'
import { MessageBubble } from './components/MessageBubble'

const QUICK_QUESTIONS = [
  'CMU 的 GPA 要求是多少？',
  'MIT 和 Stanford 的申請截止日期比較',
  'UCSD 教授的研究方向有哪些？',
  'UIUC CS 碩士需要哪些申請文件？',
]

export default function App() {
  const { messages, isStreaming, sendMessage, clearChat } = useStreamChat()
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex h-screen overflow-hidden bg-mesh font-sans text-gray-800 transition-colors duration-300">
      
      {/* ─── 側邊欄 Sidebar ─── */}
      <aside className="w-64 h-screen bg-[#1e1e24] text-gray-300 flex flex-col pt-6 pb-4 px-3 shrink-0 absolute md:static z-40 transition-transform -translate-x-full md:translate-x-0">
        
        {/* 履歷上傳區域 */}
        <ResumeUpload />

        {/* 對話紀錄佔位 (目前依要求隱藏) */}
        <div className="flex-1 overflow-y-auto space-y-1 pr-2 custom-scrollbar">
          <p className="text-[10px] text-gray-600 px-2 mt-4 text-center">對話紀錄功能已停用</p>
        </div>

        {/* 底部設定 */}
        <div className="mt-auto pt-4 border-t border-gray-800 space-y-1">
          <button 
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-3 w-full text-left px-3 py-2 rounded-lg hover:bg-[#2d2d34] transition-colors"
          >
            <Settings size={18} className="text-gray-400" />
            <span className="text-sm">Settings</span>
          </button>
        </div>
      </aside>

      {/* ─── 主對話區域 Chat Main ─── */}
      <main className="flex-1 flex flex-col relative min-w-0 transition-colors duration-300">
        
        {/* 頂部導航欄 Header */}
        <header className="absolute top-0 inset-x-0 z-10 glass border-b border-gray-200/50 px-6 py-4 shrink-0 transition-all flex items-center gap-4">
          {/* 行動裝置側邊選單按鈕 */}
          <button className="md:hidden p-2 -ml-2 text-gray-500 hover:text-gray-800 rounded-lg hover:bg-gray-100 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
          </button>
          
          <div className="flex-1 flex items-center justify-between">
            <div>
              <h1 
                onClick={clearChat}
                className="text-xl font-display font-semibold text-gray-900 tracking-tight cursor-pointer hover:text-indigo-600 transition-colors inline-block"
              >
                留學顧問 AI
              </h1>
              <p className="text-gray-500 text-xs mt-0.5 font-medium">北美 CS 研究所申請諮詢助理</p>
            </div>
          </div>
        </header>

        {/* 對話視窗 Main Scroll Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 pt-24 pb-32 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-4">
            
            {/* 首頁引導畫面 */}
            {messages.length === 0 && (
              <div className="text-center mt-16 px-4 animate-fade-in-up">
                <p className="text-5xl mb-4">🎓</p>
                <p className="text-base font-medium text-gray-600">有什麼想了解的嗎？</p>
                <p className="text-sm text-gray-400 mt-1 mb-8 max-w-sm mx-auto">
                  我可以協助您查詢各校 GPA、語言要求、截止日期，以及教授的研究方向。
                </p>
                
                {/* 快速提問按鈕區 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto">
                  {QUICK_QUESTIONS.map((q, i) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="text-left text-sm text-gray-600 bg-white/60 backdrop-blur-sm border border-gray-200/60 rounded-xl px-4 py-3.5 hover:border-indigo-300 hover:text-indigo-600 hover:bg-white hover:-translate-y-0.5 transition-all duration-200 shadow-sm hover:shadow-md cursor-pointer group"
                      style={{ animationDelay: `${150 + i * 50}ms` }}
                    >
                      <span className="flex items-center justify-between">
                        <span>{q}</span>
                        <span className="text-indigo-300 group-hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 訊息泡泡列表 */}
            {messages.map(msg => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            <div ref={bottomRef} className="h-4" />
          </div>
        </div>

        {/* 對話輸入框 */}
        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </main>

      {/* 設定彈窗 */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </div>
  )
}
