import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import type { AgentEvent, Message } from '../types'

export function useStreamChat() {
  const [messages, setMessages] = useState<Message[]>([])

  const mutation = useMutation({
    mutationFn: async (query: string) => {
      const assistantId = crypto.randomUUID()

      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'user',
          text: query,
          events: [],
          loading: false,
        },
        {
          id: assistantId,
          role: 'assistant',
          text: '',
          events: [],
          loading: true,
        },
      ])

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event: AgentEvent = JSON.parse(line.slice(6))
            setMessages(prev =>
              prev.map(m => {
                if (m.id !== assistantId) return m
                const base = { ...m, events: [...m.events, event] }
                if (event.type === 'answer')
                  return { ...base, text: event.text, loading: false }
                if (event.type === 'error')
                  return { ...base, text: event.message, loading: false, error: true }
                return base
              })
            )
          } catch {
            // ignore malformed SSE line
          }
        }
      }
    },

    onError: () => {
      setMessages(prev => {
        const last = [...prev].reverse().find(m => m.role === 'assistant' && m.loading)
        if (!last) return prev
        return prev.map(m =>
          m.id === last.id
            ? { ...m, loading: false, error: true, text: '連線錯誤，請稍後再試。' }
            : m
        )
      })
    },
  })

  return {
    messages,
    isStreaming: mutation.isPending,
    sendMessage: (query: string) => mutation.mutate(query),
  }
}
