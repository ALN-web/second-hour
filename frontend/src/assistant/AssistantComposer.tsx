import { useState, useRef, useEffect } from 'react'

interface AssistantComposerProps {
  onSendMessage: (text: string) => void
  disabled?: boolean
  loading?: boolean
}

export function AssistantComposer({
  onSendMessage,
  disabled = false,
  loading = false,
}: AssistantComposerProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!loading && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [loading])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled || loading) return
    onSendMessage(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    // Auto-adjust height
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  const quickPills = [
    'Check my vehicle insurance status',
    'What documents are in my wallet?',
    'What is the PM-RAHAT ₹1.5L cover?',
    'Accident case progress & tasks',
  ]

  return (
    <div className="border-t border-[#1a3152] bg-[#071324] p-3 sm:p-4">
      <div className="max-w-4xl mx-auto space-y-2.5">
        {/* Quick query pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-[11px]">
          <span className="text-slate-400 shrink-0 font-medium">Quick prompts:</span>
          {quickPills.map((pill, idx) => (
            <button
              key={idx}
              type="button"
              disabled={disabled || loading}
              onClick={() => {
                setText(pill)
                if (textareaRef.current) {
                  textareaRef.current.focus()
                }
              }}
              className="shrink-0 px-2.5 py-1 rounded-full bg-[#0c1d35] hover:bg-[#122847] border border-[#1b3457] hover:border-[#ff7518]/50 text-slate-300 hover:text-white transition cursor-pointer"
            >
              {pill}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="relative flex items-end gap-2 bg-[#0a182d] border border-[#1e385c] focus-within:border-[#ff7518] rounded-2xl p-2 transition-all shadow-inner">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            placeholder="Ask about your vehicles, insurance expiry, documents, accident cases, or PM-RAHAT rules..."
            className="w-full bg-transparent text-sm text-white placeholder-slate-400 focus:outline-none resize-none px-2 py-1.5 max-h-40 leading-relaxed disabled:opacity-50"
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled || loading}
            className={`shrink-0 p-2.5 rounded-xl transition-all duration-150 flex items-center justify-center ${
              text.trim() && !disabled && !loading
                ? 'bg-[#ff7518] hover:bg-[#ea6309] text-white shadow-md shadow-[#ff7518]/25 cursor-pointer scale-100 hover:scale-105 active:scale-95'
                : 'bg-[#14263f] text-slate-400 cursor-not-allowed opacity-60'
            }`}
            title="Send message (Enter)"
          >
            {loading ? (
              <svg className="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            )}
          </button>
        </div>

        {/* Footer info line */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <span>Press <kbd className="px-1 py-0.5 rounded bg-[#10233d] text-slate-300 font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-[#10233d] text-slate-300 font-mono text-[10px]">Shift+Enter</kbd> for newline</span>
          <span className="flex items-center gap-1 text-slate-400">
            <span>In an emergency, dial</span>
            <a href="tel:112" className="text-red-400 font-bold hover:underline">112</a>
          </span>
        </div>
      </div>
    </div>
  )
}
