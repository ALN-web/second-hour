import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import type { ActionCard, ConversationDetail, ConversationItem, MessageItem } from './types'
import { AssistantSidebar } from './AssistantSidebar'
import { AssistantWelcome } from './AssistantWelcome'
import { AssistantMessage } from './AssistantMessage'
import { AssistantComposer } from './AssistantComposer'

interface AssistantModuleProps {
  user: { user_id: string; name: string; role_label: string } | null
  onNavigateToVehicles?: (vehicleId?: string) => void
  onNavigateToDocuments?: () => void
  onNavigateToCases?: (caseId?: string) => void
  onBackHome?: () => void
}

export function AssistantModule({
  user,
  onNavigateToVehicles,
  onNavigateToDocuments,
  onNavigateToCases,
  onBackHome,
}: AssistantModuleProps) {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [currentConvId, setCurrentConvId] = useState<string | null>(null)
  const [currentConv, setCurrentConv] = useState<ConversationDetail | null>(null)
  const [, setLoadingConvs] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [actionNotice, setActionNotice] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom whenever messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentConv?.messages, sending])

  // Load conversations on mount or user switch
  useEffect(() => {
    loadConversations()
  }, [user?.user_id])

  const loadConversations = async (autoSelectId?: string) => {
    try {
      setLoadingConvs(true)
      const data = await api('/api/ai/conversations')
      setConversations(data)

      if (autoSelectId) {
        selectConversation(autoSelectId)
      } else if (data.length > 0 && !currentConvId) {
        selectConversation(data[0].id)
      } else if (data.length === 0) {
        setCurrentConvId(null)
        setCurrentConv(null)
      }
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      setLoadingConvs(false)
    }
  }

  const selectConversation = async (convId: string) => {
    try {
      setCurrentConvId(convId)
      setLoadingMessages(true)
      const detail: ConversationDetail = await api(`/api/ai/conversations/${convId}`)
      setCurrentConv(detail)
    } catch (e) {
      console.error(`Failed to load conversation ${convId}:`, e)
    } finally {
      setLoadingMessages(false)
    }
  }

  const handleNewConversation = async () => {
    try {
      const newConv = await api('/api/ai/conversations', {
        method: 'POST',
        body: { title: 'New Conversation' },
      })
      setCurrentConvId(newConv.id)
      setCurrentConv({
        id: newConv.id,
        title: newConv.title,
        is_pinned: false,
        created_at: newConv.created_at,
        updated_at: newConv.updated_at,
        messages: [],
      })
      await loadConversations(newConv.id)
    } catch (e) {
      console.error('Failed to create new conversation:', e)
    }
  }

  const handleDeleteConversation = async (convId: string) => {
    try {
      await api(`/api/ai/conversations/${convId}`, { method: 'DELETE' })
      const updated = conversations.filter(c => c.id !== convId)
      setConversations(updated)
      if (currentConvId === convId) {
        if (updated.length > 0) {
          selectConversation(updated[0].id)
        } else {
          setCurrentConvId(null)
          setCurrentConv(null)
        }
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  const handleClearHistory = async () => {
    try {
      await api('/api/ai/conversations', { method: 'DELETE' })
      setConversations([])
      setCurrentConvId(null)
      setCurrentConv(null)
    } catch (e) {
      console.error('Failed to clear conversations:', e)
    }
  }

  const handleTogglePin = async (convId: string, currentPinned: boolean) => {
    try {
      await api(`/api/ai/conversations/${convId}/pin`, {
        method: 'PATCH',
        body: { pinned: !currentPinned },
      })
      await loadConversations(currentConvId || undefined)
    } catch (e) {
      console.error('Failed to toggle pin:', e)
    }
  }

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || sending) return

    let activeId = currentConvId
    // If no active conversation, create one first
    if (!activeId) {
      try {
        const created = await api('/api/ai/conversations', {
          method: 'POST',
          body: { title: text.slice(0, 36) },
        })
        activeId = created.id
        setCurrentConvId(activeId)
      } catch (e) {
        console.error('Failed to auto-create conversation:', e)
        return
      }
    }

    // Optimistic user message
    const tempUserMsg: MessageItem = {
      id: `temp_${Date.now()}`,
      sender: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    setCurrentConv(prev => {
      const msgs = prev ? [...prev.messages, tempUserMsg] : [tempUserMsg]
      return {
        id: activeId!,
        title: prev?.title || text.slice(0, 36),
        is_pinned: prev?.is_pinned || false,
        created_at: prev?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
        messages: msgs,
      }
    })

    try {
      setSending(true)
      const res = await api(`/api/ai/conversations/${activeId}/messages`, {
        method: 'POST',
        body: { content: text },
      })

      const asstMsg: MessageItem = {
        id: res.id,
        sender: 'assistant',
        content: res.content,
        citations: res.citations || [],
        action_cards: res.action_cards || [],
        suggested_followups: res.suggested_followups || [],
        created_at: res.created_at,
      }

      setCurrentConv(prev => prev ? {
        ...prev,
        title: res.conversation_title || prev.title,
        messages: [...prev.messages.filter(m => m.id !== tempUserMsg.id), tempUserMsg, asstMsg],
      } : null)

      // Refresh list to update title & last message preview
      loadConversations(activeId || undefined)
    } catch (e) {
      console.error('Failed to send message:', e)
    } finally {
      setSending(false)
    }
  }

  const handleExecuteAction = async (action: ActionCard) => {
    try {
      const res = await api('/api/ai/actions/execute', {
        method: 'POST',
        body: {
          action_type: action.action_type,
          payload: action.payload,
        },
      })

      if (res.message) {
        setActionNotice(res.message)
        setTimeout(() => setActionNotice(null), 4000)
      }

      // Check if navigation is requested
      if (res.path) {
        const path: string = res.path
        if (path.startsWith('/vehicles')) {
          const vId = path.split('/')[2]
          if (onNavigateToVehicles) onNavigateToVehicles(vId)
        } else if (path.startsWith('/documents')) {
          if (onNavigateToDocuments) onNavigateToDocuments()
        } else if (path.startsWith('/cases')) {
          const cId = path.split('/')[2]
          if (onNavigateToCases) onNavigateToCases(cId)
        }
      }
    } catch (e) {
      console.error('Failed to execute action:', e)
    }
  }

  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-[#07111e]">
      {/* Sidebar (desktop and mobile drawer) */}
      <AssistantSidebar
        conversations={conversations}
        currentConvId={currentConvId}
        onSelectConversation={selectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onTogglePin={handleTogglePin}
        onClearHistory={handleClearHistory}
        userName={user?.name}
        roleLabel={user?.role_label}
        isOpen={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-[#091528] relative">
        {/* Chat Header Bar */}
        <div className="h-14 border-b border-[#1a3152] bg-[#071221] px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-[#12233c]"
              title="Open conversations drawer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
              <h1 className="text-sm font-bold text-white truncate">
                {currentConv ? currentConv.title : 'Ask Second Hour AI'}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#0d223f] border border-[#1d3d66] text-[11px] text-slate-300">
              <span className="w-1.5 h-1.5 rounded-full bg-[#ff7518]" />
              <span>Grounded Context Active</span>
            </span>

            {onBackHome && (
              <button
                onClick={onBackHome}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#12233c] text-xs flex items-center gap-1"
                title="Return to Homepage"
              >
                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span className="hidden md:inline">Home</span>
              </button>
            )}

            <button
              onClick={handleNewConversation}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#12233c] text-xs flex items-center gap-1"
              title="Start a new chat"
            >
              <svg className="w-4 h-4 text-[#ff7518]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden md:inline">New Chat</span>
            </button>
          </div>
        </div>

        {/* Action feedback toast */}
        {actionNotice && (
          <div className="absolute top-16 right-4 z-20 px-4 py-2.5 rounded-xl bg-emerald-950/90 border border-emerald-500/50 text-emerald-200 text-xs shadow-xl flex items-center gap-2 animate-fade-in">
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
            </svg>
            <span>{actionNotice}</span>
          </div>
        )}

        {/* Message Container / Welcome Screen */}
        <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin">
          {loadingMessages ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <div className="w-8 h-8 mx-auto border-2 border-[#ff7518] border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-slate-400">Loading conversation context...</p>
              </div>
            </div>
          ) : !currentConv || currentConv.messages.length === 0 ? (
            <AssistantWelcome
              userName={user?.name}
              onSelectPrompt={handleSendMessage}
            />
          ) : (
            <div className="max-w-4xl mx-auto">
              {currentConv.messages.map((msg) => (
                <AssistantMessage
                  key={msg.id}
                  message={msg}
                  userName={user?.name}
                  onSelectFollowup={handleSendMessage}
                  onExecuteAction={handleExecuteAction}
                />
              ))}

              {/* Sending state bubble */}
              {sending && (
                <div className="flex justify-start items-start gap-3 my-4">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#ff7518] to-[#d85800] text-white flex items-center justify-center shrink-0 mt-1 shadow-md shadow-[#ff7518]/25">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div className="bg-[#0b1b31] border border-[#1b3457] rounded-2xl rounded-tl-sm px-4 py-3 text-slate-300 text-xs shadow-md flex items-center gap-2.5">
                    <span className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-[#ff7518] animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#ff7518] animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-[#ff7518] animate-bounce" style={{ animationDelay: '300ms' }} />
                    </span>
                    <span className="text-slate-400">Consulting your records & official guidance...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Composer */}
        <AssistantComposer
          onSendMessage={handleSendMessage}
          loading={sending}
        />
      </main>
    </div>
  )
}
