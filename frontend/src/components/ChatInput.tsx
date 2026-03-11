import { useState } from 'react'

interface Props {
  onSend: (query: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div className="absolute bottom-6 inset-x-0 px-4 z-20 pointer-events-none transition-all">
      <div className="max-w-3xl mx-auto flex flex-col items-center">
        {/* Shadow/Blur wrapper */}
        <div className="relative w-full max-w-2xl group pointer-events-auto">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-3xl blur opacity-30 group-hover:opacity-60 transition duration-500" />
          
          <form onSubmit={handleSubmit} className="relative flex items-end bg-white/80 backdrop-blur-2xl border border-gray-200/60 shadow-[0_8px_30px_rgb(0,0,0,0.06)] rounded-3xl p-1.5 transition-all focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-300/50">
            <textarea
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              rows={1}
              placeholder="詢問北美 CS 研究所申請相關問題… (Shift+Enter 換行)"
              className="flex-1 resize-none bg-transparent px-4 py-3.5 text-sm text-gray-800 placeholder-gray-400 focus:outline-none disabled:opacity-50 leading-relaxed max-h-[40vh] min-h-[52px] overflow-y-auto custom-scrollbar"
            />
            
            <button
              type="submit"
              disabled={disabled || !value.trim()}
              className="mb-1 mr-1 flex items-center justify-center w-10 h-10 bg-indigo-600/90 text-white rounded-2xl hover:bg-indigo-600 hover:shadow-md hover:scale-105 active:scale-95 transition-all disabled:opacity-40 disabled:hover:scale-100 disabled:cursor-not-allowed shrink-0"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 translate-x-px -translate-y-px">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>
          
          <p className="text-[10px] text-gray-400 text-center mt-3 tracking-wide">
            AI 留學顧問可能產生不準確的資訊，請以學校官網為準。
          </p>
        </div>
      </div>
    </div>
  )
}
