import { useState, useRef, useEffect } from 'react'
import { api } from '../api'
import type { WatcherAlertItem } from './types'

interface CaseAssistantDrawerProps {
  isOpen: boolean
  onClose: () => void
  caseId: string
  caseNumber: string
  victimName?: string
  alerts: WatcherAlertItem[]
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export function CaseAssistantDrawer({
  isOpen,
  onClose,
  caseId,
  caseNumber,
  victimName,
  alerts,
}: CaseAssistantDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hello! I am your Second Hour Case Assistant for case **${caseNumber}** (${victimName || 'Patient'}). I can help you understand the PM-RAHAT cashless cover, verify required documents, draft police intimations, and track surveyor next steps. How can I assist you right now?`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!isOpen) return null

  const handleSend = async (textToSend?: string) => {
    const q = textToSend || input.trim()
    if (!q || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: q }])
    if (!textToSend) setInput('')
    setLoading(true)

    try {
      const res = await api<{ reply: string }>(`/api/cases/${caseId}/chat`, {
        method: 'POST',
        body: { message: q },
      })
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.reply || 'I have noted this in the case record.' },
      ])
    } catch {
      // Friendly fallback if model offline
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Under PM-RAHAT statutory guidelines, road accident victims in India are entitled to up to ₹1,50,000 cashless stabilization and treatment for the first 7 days from the accident date. Ensure your Medico-Legal Case (MLC) intimation and hospital interim bills are uploaded in the Evidence tab.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const quickPrompts = [
    'What documents are required for PM-RAHAT?',
    'Explain the ₹1.5L cashless cover limit',
    'How do I approve the police intimation draft?',
    'What are the next steps for motor insurance?',
  ]

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200">
        {/* Drawer Header */}
        <div className="bg-navy-950 text-white p-4 flex items-center justify-between border-b border-navy-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-500/20 text-accent-500 flex items-center justify-center font-bold text-sm">
              🤖
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <span>AI Case Assistant</span>
                <span className="chip bg-white/10 text-slate-300 text-[10px] px-1.5 py-0.2 rounded font-mono">
                  {caseNumber}
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">PM-RAHAT & Post-Crash Guidance</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg p-1 transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Watcher Alerts Bar if any */}
        {alerts.length > 0 && (
          <div className="bg-amber-50 p-2.5 border-b border-amber-200 text-xs text-amber-900 flex items-center gap-2">
            <span>⚠️</span>
            <span className="font-semibold">{alerts[0].title}:</span>
            <span className="truncate text-[11px] text-amber-800">{alerts[0].message}</span>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-slate-50/50">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-accent-500 text-white rounded-br-xs'
                    : 'bg-white border border-slate-200 text-navy-950 shadow-2xs rounded-bl-xs'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-slate-200 rounded-2xl px-4 py-2 text-xs text-slate-500 flex items-center gap-1.5">
                <span className="animate-pulse">Thinking...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts */}
        <div className="p-3 bg-white border-t border-slate-100 overflow-x-auto flex gap-1.5">
          {quickPrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => handleSend(p)}
              className="text-[11px] font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 px-2.5 py-1 rounded-full whitespace-nowrap transition cursor-pointer"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-3 bg-white border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about this case or PM-RAHAT..."
              className="flex-1 text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-1 focus:ring-accent-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="btn-accent px-4 py-2.5 rounded-xl text-xs font-semibold shadow disabled:opacity-50 cursor-pointer"
            >
              Send
            </button>
          </form>
          <p className="text-[10px] text-slate-400 text-center mt-1.5">
            Guidance based on case documents & PM-RAHAT rules. In an emergency, call 112.
          </p>
        </div>
      </div>
    </div>
  )
}
