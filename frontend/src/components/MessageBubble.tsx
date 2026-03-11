import { User, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../types'
import { AgentSteps } from './AgentSteps'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end animate-fade-in-up w-full">
        <div className="flex gap-4 max-w-[85%] sm:max-w-[75%] items-start justify-end">
          <div className="bg-white/80 backdrop-blur-sm text-gray-800 rounded-3xl rounded-tr-sm px-5 py-3.5 text-sm leading-relaxed shadow-sm border border-gray-100 order-1">
            {message.text}
          </div>
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0 order-2 overflow-hidden border border-gray-300">
            <User size={16} className="text-gray-500" strokeWidth={2.5} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start animate-fade-in-up w-full group">
      <div className="flex gap-4 max-w-[95%] sm:max-w-[85%] items-start">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex flex-col items-center justify-center shrink-0 shadow-md">
           <Sparkles size={14} className="text-white" strokeWidth={2.5} />
        </div>
        
        <div className="flex-1 space-y-3 pt-1">
          <AgentSteps events={message.events} />

          {message.loading && !message.text ? (
            <div className="flex gap-1.5 items-center h-6 px-1">
              <span
                className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                style={{ animationDelay: '0ms' }}
              />
              <span
                className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                style={{ animationDelay: '150ms' }}
              />
              <span
                className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                style={{ animationDelay: '300ms' }}
              />
            </div>
          ) : (
            <div
              className={`text-[15px] leading-relaxed tracking-wide prose prose-sm max-w-none prose-p:my-1.5 prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline prose-li:my-0.5 ${
                message.error ? 'text-red-500' : 'text-gray-800'
              }`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.text}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
