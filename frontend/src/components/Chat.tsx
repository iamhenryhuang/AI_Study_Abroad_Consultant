import { useEffect, useRef } from 'react'
import { ChatInput } from './ChatInput'
import { MessageBubble } from './MessageBubble'
import { useStreamChat } from '../hooks/useStreamChat'

const QUICK_QUESTIONS = [
  'CMU 的 GPA 要求是多少？',
  'MIT 和 Stanford 的申請截止日期比較',
  'UCSD 教授的研究方向有哪些？',
  'UIUC CS 碩士需要哪些申請文件？',
]

export function Chat() {
  const { messages, isStreaming, sendMessage } = useStreamChat()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 flex flex-col relative min-w-0">
      {/* Header */}
      <header className="absolute top-0 inset-x-0 z-10 glass border-b border-gray-200/50 px-6 py-4 shrink-0 transition-all flex items-center gap-4">
        {/* Mobile Sidebar Toggle Placeholder */}
        <button className="md:hidden p-2 -ml-2 text-gray-500 hover:text-gray-800 rounded-lg hover:bg-gray-100 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
        </button>
        
        <div className="flex-1 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-display font-semibold text-gray-900 tracking-tight">留學顧問 AI</h1>
            <p className="text-gray-500 text-xs mt-0.5 font-medium">北美 CS 研究所申請諮詢助理</p>
          </div>
        </div>
      </header>

      {/* Chat window */}
      <main className="flex-1 overflow-y-auto px-4 py-6 pt-24 pb-32 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-4">

          {messages.length === 0 && (
            <div className="text-center mt-16">
              <p className="text-5xl mb-4">🎓</p>
              <p className="text-base font-medium text-gray-600">有什麼想了解的嗎？</p>
              <p className="text-sm text-gray-400 mt-1 mb-8">
                可以問我各校 GPA、TOEFL 要求、申請截止日期、教授研究方向…
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '100ms' }}>
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

          {messages.map(msg => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
