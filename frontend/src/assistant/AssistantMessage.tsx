import { useState } from 'react'
import type { ActionCard, Citation, MessageItem } from './types'

interface AssistantMessageProps {
  message: MessageItem
  onSelectFollowup?: (question: string) => void
  onExecuteAction?: (action: ActionCard) => void
  userName?: string
}

export function AssistantMessage({
  message,
  onSelectFollowup,
  onExecuteAction,
  userName = 'Priya',
}: AssistantMessageProps) {
  const isUser = message.sender === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isUser) {
    return (
      <div className="flex justify-end items-start gap-3 my-4">
        <div className="max-w-2xl bg-gradient-to-r from-[#17335c] to-[#122847] border border-[#2b4c7e]/60 rounded-2xl rounded-tr-sm px-4 py-3 text-white text-sm shadow-md">
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          <div className="mt-1 text-right text-[10px] text-slate-400">
            {formatTime(message.created_at)}
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-[#1e3a61] border border-[#2b4c7e] text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
          {userName.slice(0, 2).toUpperCase()}
        </div>
      </div>
    )
  }

  // Assistant Message
  return (
    <div className="flex justify-start items-start gap-3 my-5">
      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#ff7518] to-[#d85800] text-white flex items-center justify-center shrink-0 mt-1 shadow-md shadow-[#ff7518]/25">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>

      <div className="flex-1 max-w-3xl space-y-3 min-w-0">
        {/* Main Response Box */}
        <div className="bg-[#0b1b31] border border-[#1b3457] rounded-2xl rounded-tl-sm p-4 text-slate-200 text-sm shadow-md relative group">
          {/* Top meta & copy button */}
          <div className="flex items-center justify-between border-b border-[#162e4f] pb-2 mb-3 text-xs text-slate-400">
            <span className="font-semibold text-white tracking-wide flex items-center gap-1.5">
              <span>Second Hour AI</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[10px]">{formatTime(message.created_at)}</span>
              <button
                onClick={handleCopy}
                className="p-1 rounded hover:bg-[#162e4f] text-slate-400 hover:text-white transition"
                title="Copy response"
              >
                {copied ? (
                  <span className="text-[10px] text-emerald-400 font-medium">Copied!</span>
                ) : (
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Formatted Markdown Content */}
          <div className="space-y-2.5 leading-relaxed text-slate-200">
            {renderMarkdown(message.content)}
          </div>
        </div>

        {/* Source Citations Block */}
        {message.citations && message.citations.length > 0 && (
          <div className="bg-[#081527] border border-[#183152] rounded-xl p-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-2">
              <svg className="w-3.5 h-3.5 text-[#ff7518]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Verified Source Citations ({message.citations.length})</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {message.citations.map((c) => (
                <CitationCard key={c.id} citation={c} />
              ))}
            </div>
          </div>
        )}

        {/* Action Cards */}
        {message.action_cards && message.action_cards.length > 0 && (
          <div className="space-y-2">
            {message.action_cards.map((card) => (
              <ActionCardView
                key={card.id}
                card={card}
                onExecute={() => onExecuteAction && onExecuteAction(card)}
              />
            ))}
          </div>
        )}

        {/* Suggested Follow-up Questions */}
        {message.suggested_followups && message.suggested_followups.length > 0 && (
          <div className="pt-1">
            <p className="text-[11px] font-medium text-slate-400 mb-1.5 flex items-center gap-1">
              <svg className="w-3 h-3 text-[#ff7518]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Suggested Follow-ups:</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {message.suggested_followups.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => onSelectFollowup && onSelectFollowup(q)}
                  className="px-3 py-1.5 rounded-full bg-[#0d203a] hover:bg-[#142e52] border border-[#1f3c66] hover:border-[#ff7518]/50 text-xs text-slate-200 hover:text-white transition text-left cursor-pointer"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function CitationCard({ citation }: { citation: Citation }) {
  const getBadge = () => {
    switch (citation.type) {
      case 'APPLICATION_RECORD':
        return { label: 'Application Record', style: 'bg-blue-500/10 text-blue-300 border-blue-500/30' }
      case 'DOCUMENT_WALLET':
        return { label: 'Document Wallet', style: 'bg-amber-500/10 text-amber-300 border-amber-500/30' }
      case 'OFFICIAL_GOVERNMENT':
        return { label: 'Official MoRTH', style: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' }
      default:
        return { label: 'Guidance', style: 'bg-slate-500/10 text-slate-300 border-slate-500/30' }
    }
  }

  const badge = getBadge()

  return (
    <div className="p-2.5 rounded-lg bg-[#0c1c33] border border-[#193355] text-xs flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${badge.style}`}>
            {badge.label}
          </span>
          {citation.verification === 'verified' && (
            <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-0.5">
              ✓ Verified
            </span>
          )}
        </div>
        <p className="font-semibold text-white line-clamp-1">{citation.title}</p>
        <p className="text-[11px] text-slate-400 line-clamp-2 mt-1 leading-normal">{citation.snippet}</p>
      </div>

      {citation.url_or_path && (
        <div className="mt-2 pt-1.5 border-t border-[#162e4f]">
          <span className="text-[10px] text-[#ff7518] truncate block">
            {citation.url_or_path}
          </span>
        </div>
      )}
    </div>
  )
}

function ActionCardView({
  card,
  onExecute,
}: {
  card: ActionCard
  onExecute: () => void
}) {
  return (
    <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#0d223f] to-[#0a182d] border border-[#244673] flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-md">
      <div className="space-y-0.5 min-w-0">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#ff7518]" />
          <h4 className="text-xs font-bold text-white tracking-wide truncate">{card.title}</h4>
        </div>
        <p className="text-xs text-slate-300">{card.description}</p>
      </div>

      <button
        onClick={onExecute}
        className="shrink-0 px-4 py-2 rounded-lg bg-[#ff7518] hover:bg-[#ea6309] text-white text-xs font-semibold shadow-md shadow-[#ff7518]/20 transition flex items-center justify-center gap-1.5 cursor-pointer"
      >
        <span>{card.button_label}</span>
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
        </svg>
      </button>
    </div>
  )
}

function formatTime(isoStr: string) {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []

  let inList = false
  let listItems: React.ReactNode[] = []

  const flushList = (key: string) => {
    if (inList) {
      elements.push(
        <ul key={key} className="space-y-1.5 my-2 pl-4 list-disc list-outside text-slate-200">
          {listItems}
        </ul>
      )
      listItems = []
      inList = false
    }
  }

  lines.forEach((line, i) => {
    const trimmed = line.trim()

    // Alert Callouts
    if (trimmed.startsWith('> [!CAUTION]')) {
      flushList(`flush-${i}`)
      elements.push(
        <div key={i} className="p-3 my-2 rounded-xl bg-red-950/60 border border-red-500/50 text-red-200 text-xs flex gap-2.5 items-start">
          <span className="text-red-400 font-bold text-base leading-none">🚨</span>
          <div>
            <strong className="text-white block mb-0.5">EMERGENCY NOTICE: Call 112</strong>
            <span>{trimmed.replace('> [!CAUTION]', '').replace('**EMERGENCY NOTICE: Call 112 Immediately**', '').trim()}</span>
          </div>
        </div>
      )
      return
    }

    if (trimmed.startsWith('>')) {
      flushList(`flush-${i}`)
      elements.push(
        <div key={i} className="p-2.5 my-2 rounded-lg bg-[#0e213b] border-l-4 border-[#ff7518] text-xs text-slate-300 italic">
          {renderInline(trimmed.replace(/^>\s*/, ''))}
        </div>
      )
      return
    }

    // Headers
    if (trimmed.startsWith('### ')) {
      flushList(`flush-${i}`)
      elements.push(
        <h3 key={i} className="text-sm font-bold text-white mt-3 mb-1 tracking-wide">
          {trimmed.slice(4)}
        </h3>
      )
      return
    }

    if (trimmed.startsWith('## ')) {
      flushList(`flush-${i}`)
      elements.push(
        <h2 key={i} className="text-base font-bold text-white mt-4 mb-1 tracking-wide">
          {trimmed.slice(3)}
        </h2>
      )
      return
    }

    // List items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      inList = true
      listItems.push(
        <li key={i} className="text-xs leading-relaxed">
          {renderInline(trimmed.slice(2))}
        </li>
      )
      return
    }

    // Blank line
    if (!trimmed) {
      flushList(`flush-${i}`)
      return
    }

    // Normal paragraph
    flushList(`flush-${i}`)
    elements.push(
      <p key={i} className="text-xs sm:text-sm leading-relaxed text-slate-200 my-1">
        {renderInline(trimmed)}
      </p>
    )
  })

  flushList('flush-final')
  return elements
}

function renderInline(text: string): React.ReactNode {
  // Parse inline bold **text** and inline code `code`
  const parts: React.ReactNode[] = []
  const regex = /(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    const token = match[0]
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="font-semibold text-white">
          {token.slice(2, -2)}
        </strong>
      )
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="px-1 py-0.5 rounded bg-[#162e4f] text-[#ff9d5c] text-[11px] font-mono">
          {token.slice(1, -1)}
        </code>
      )
    } else if (token.startsWith('[') && token.includes('](')) {
      const labelMatch = token.match(/\[(.*?)\]\((.*?)\)/)
      if (labelMatch) {
        parts.push(
          <a
            key={match.index}
            href={labelMatch[2]}
            target="_blank"
            rel="noreferrer"
            className="text-[#ff7518] hover:underline font-medium"
          >
            {labelMatch[1]}
          </a>
        )
      }
    }
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts
}
