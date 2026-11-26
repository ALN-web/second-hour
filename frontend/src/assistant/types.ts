export type CitationType =
  | 'APPLICATION_RECORD'
  | 'DOCUMENT_WALLET'
  | 'OFFICIAL_GOVERNMENT'
  | 'GENERAL_GUIDANCE'

export interface Citation {
  id: string
  type: CitationType
  title: string
  snippet: string
  url_or_path?: string
  verification?: string
}

export type ActionType =
  | 'NAVIGATE'
  | 'OPEN_DOCUMENT'
  | 'OPEN_CASE'
  | 'CREATE_TASK'
  | 'PREPARE_REPORT'
  | 'INITIATE_UPLOAD'

export interface ActionCard {
  id: string
  action_type: ActionType
  title: string
  description: string
  payload: Record<string, any>
  button_label: string
  status?: 'proposed' | 'executed' | 'dismissed'
}

export interface MessageItem {
  id: string
  sender: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  action_cards?: ActionCard[]
  suggested_followups?: string[]
  created_at: string
}

export interface ConversationItem {
  id: string
  title: string
  is_pinned: boolean
  last_message?: string | null
  last_message_at?: string | null
  created_at: string
  updated_at: string
}

export interface ConversationDetail {
  id: string
  title: string
  is_pinned: boolean
  created_at: string
  updated_at: string
  messages: MessageItem[]
}
