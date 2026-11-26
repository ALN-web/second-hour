import { useState } from 'react'
import type { ConversationItem } from './types'

interface AssistantSidebarProps {
  conversations: ConversationItem[]
  currentConvId: string | null
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
  onDeleteConversation: (id: string) => void
  onTogglePin: (id: string, currentPinned: boolean) => void
  onClearHistory: () => void
  userName?: string
  roleLabel?: string
  isOpen: boolean
  onClose: () => void
}

export function AssistantSidebar({
  conversations,
  currentConvId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onTogglePin,
  onClearHistory,
  userName = 'Priya',
  roleLabel = 'Family coordinator',
  isOpen,
  onClose,
}: AssistantSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [confirmClear, setConfirmClear] = useState(false)

  const filtered = conversations.filter(c =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.last_message && c.last_message.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const pinnedConvs = filtered.filter(c => c.is_pinned)
  const regularConvs = filtered.filter(c => !c.is_pinned)

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-40 w-72 sm:w-80 bg-[#091528] border-r border-[#1a3152] flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-[#1a3152] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#ff7518] to-[#e65c00] flex items-center justify-center text-white shadow-md shadow-[#ff7518]/20">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Ask Second Hour</h2>
              <span className="text-[11px] text-slate-400">Context-Aware AI Assistant</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded text-slate-400 hover:text-white hover:bg-[#12233c]"
            title="Close sidebar"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={onNewConversation}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-semibold text-sm text-white bg-[#ff7518] hover:bg-[#ea6309] shadow-md shadow-[#ff7518]/20 transition-all duration-150 hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" />
            </svg>
            <span>New Conversation</span>
          </button>
        </div>

        {/* Search input */}
        <div className="px-3 pb-2">
          <div className="relative">
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0d1d35] border border-[#1b3152] rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-[#ff7518] transition"
            />
            <svg className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center py-10 px-4">
              <p className="text-xs text-slate-400">No conversation history yet.</p>
              <p className="text-[11px] text-slate-500 mt-1">Start a new chat to consult your vehicles, documents, or cases.</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-6 px-4">
              <p className="text-xs text-slate-400">No matching chats found.</p>
            </div>
          ) : (
            <>
              {/* Pinned section */}
              {pinnedConvs.length > 0 && (
                <div className="mb-2">
                  <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <svg className="w-3 h-3 text-[#ff7518]" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                    </svg>
                    <span>Pinned</span>
                  </div>
                  {pinnedConvs.map(c => (
                    <ConversationRow
                      key={c.id}
                      item={c}
                      active={c.id === currentConvId}
                      onSelect={() => {
                        onSelectConversation(c.id)
                        onClose()
                      }}
                      onDelete={() => onDeleteConversation(c.id)}
                      onTogglePin={() => onTogglePin(c.id, c.is_pinned)}
                    />
                  ))}
                </div>
              )}

              {/* Regular section */}
              {regularConvs.length > 0 && (
                <div>
                  {pinnedConvs.length > 0 && (
                    <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      Recent Chats
                    </div>
                  )}
                  {regularConvs.map(c => (
                    <ConversationRow
                      key={c.id}
                      item={c}
                      active={c.id === currentConvId}
                      onSelect={() => {
                        onSelectConversation(c.id)
                        onClose()
                      }}
                      onDelete={() => onDeleteConversation(c.id)}
                      onTogglePin={() => onTogglePin(c.id, c.is_pinned)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer with Clear History & User Info */}
        <div className="p-3 border-t border-[#1a3152] bg-[#071120] space-y-2">
          {conversations.length > 0 && (
            <div className="pt-1">
              {confirmClear ? (
                <div className="flex items-center justify-between gap-2 p-1.5 bg-red-950/40 border border-red-800/50 rounded-lg">
                  <span className="text-[11px] text-red-300">Clear all chats?</span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => {
                        onClearHistory()
                        setConfirmClear(false)
                      }}
                      className="px-2 py-0.5 text-[10px] font-semibold bg-red-600 hover:bg-red-700 text-white rounded"
                    >
                      Yes
                    </button>
                    <button
                      onClick={() => setConfirmClear(false)}
                      className="px-2 py-0.5 text-[10px] text-slate-300 hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmClear(true)}
                  className="w-full text-left px-2 py-1 text-[11px] text-slate-400 hover:text-red-400 flex items-center gap-1.5 rounded transition"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>Clear Conversation History</span>
                </button>
              )}
            </div>
          )}

          {/* User profile capsule */}
          <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg bg-[#0d1d35]/60 border border-[#1b3152]/60">
            <div className="w-7 h-7 rounded-full bg-[#1e3a61] border border-[#2b4c7e] text-white flex items-center justify-center text-xs font-bold">
              {userName.slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">{userName}</p>
              <p className="text-[10px] text-slate-400 truncate">{roleLabel}</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-400 ring-4 ring-emerald-400/20" title="Connected & Grounded" />
          </div>
        </div>
      </aside>
    </>
  )
}

function ConversationRow({
  item,
  active,
  onSelect,
  onDelete,
  onTogglePin,
}: {
  item: ConversationItem
  active: boolean
  onSelect: () => void
  onDelete: () => void
  onTogglePin: () => void
}) {
  const [showOptions, setShowOptions] = useState(false)

  return (
    <div
      onMouseEnter={() => setShowOptions(true)}
      onMouseLeave={() => setShowOptions(false)}
      className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-left transition-all ${
        active
          ? 'bg-[#122847] text-white border border-[#ff7518]/50 shadow-sm'
          : 'text-slate-300 hover:bg-[#0e213b] hover:text-white border border-transparent'
      }`}
      onClick={onSelect}
    >
      <div className="flex-1 min-w-0 pr-2">
        <div className="flex items-center gap-1.5">
          {item.is_pinned && (
            <svg className="w-2.5 h-2.5 text-[#ff7518] shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
            </svg>
          )}
          <p className="text-xs font-medium truncate">{item.title || 'Untitled Chat'}</p>
        </div>
        {item.last_message && (
          <p className="text-[11px] text-slate-400 truncate mt-0.5">{item.last_message}</p>
        )}
      </div>

      {/* Action buttons (Pin / Delete) */}
      <div
        className={`flex items-center gap-1 shrink-0 ${
          showOptions || active ? 'opacity-100' : 'opacity-0'
        } transition-opacity`}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onTogglePin}
          className={`p-1 rounded hover:bg-[#1a355c] ${
            item.is_pinned ? 'text-[#ff7518]' : 'text-slate-400 hover:text-slate-200'
          }`}
          title={item.is_pinned ? 'Unpin' : 'Pin conversation'}
        >
          <svg className="w-3.5 h-3.5" fill={item.is_pinned ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </button>
        <button
          onClick={onDelete}
          className="p-1 rounded hover:bg-red-950/60 text-slate-400 hover:text-red-400"
          title="Delete conversation"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  )
}
