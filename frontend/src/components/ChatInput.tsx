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
    <div className="absolute bottom-0 inset-x-0 w-full z-20 pointer-events-none pb-4 pt-8 bg-linear-to-t from-white via-white to-transparent">
      <div className="max-w-3xl mx-auto flex flex-col items-center px-4 md:px-0">
        
        <div className="relative w-full pointer-events-auto">
          <form onSubmit={handleSubmit} className="relative flex items-end bg-gray-50 border border-gray-200/80 rounded-2xl p-2 transition-all focus-within:bg-white focus-within:shadow-[0_0_15px_rgba(0,0,0,0.05)] focus-within:border-gray-300">
            <textarea
              value={value}
              onChange={e => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              rows={1}
              placeholder="傳送訊息給留學顧問 AI... (Shift+Enter 換行)"
              className="flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] text-gray-800 placeholder-gray-500 focus:outline-none disabled:opacity-50 max-h-[200px] min-h-[44px] overflow-y-auto custom-scrollbar"
            />

            <button
              type="submit"
              disabled={disabled || !value.trim()}
              className="mb-1 mr-1 flex items-center justify-center w-8 h-8 rounded-lg bg-black text-white hover:bg-gray-800 transition-colors disabled:opacity-30 disabled:bg-gray-200 disabled:text-gray-500 disabled:cursor-not-allowed shrink-0"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 translate-x-px -translate-y-px">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </form>

          <p className="text-[11px] text-gray-400 text-center mt-2.5">
            AI 可能犯錯。請查閱官方網站以獲得最新資訊。
          </p>
        </div>
      </div>
    </div>
  )
}
