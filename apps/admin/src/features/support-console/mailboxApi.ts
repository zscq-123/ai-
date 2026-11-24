export type QQMailboxTestResult = {
  connected: boolean
  server: string
  messages: number
  unread: number
  last_uid: number
}

export type QQSyncedMessage = {
  uid: number
  message_id: string
  sender_name: string
  sender_email: string
  subject: string
  text: string
  received_at: string
}

export type QQMailboxSyncResult = {
  last_uid: number
  messages: QQSyncedMessage[]
}

export type LocalMailboxConversation = {
  id: string
  name: string
  initials: string
  store_id: string
  subject: string
  preview: string
  time: string
  unread: boolean
  urgent: boolean
  color: string
  text: string
  mailbox_id?: string | null
  mailbox_uid?: number | null
  sender_email?: string | null
  message_id?: string | null
}

export type LocalMailboxAccount = {
  id: string
  email: string
  provider: string
  store_id: string
  enabled: boolean
  connection: 'imap-verified'
  messages: number
  unread: number
  last_uid: number
}

export type StorefrontConversation = {
  id: string
  name: string
  initials: string
  store_id: string
  subject: string
  preview: string
  time: string
  unread: boolean
  urgent: boolean
  status: 'open' | 'resolved'
  color: string
  messages: { role: 'customer' | 'agent'; text: string; time: string }[]
  handoff_status: 'none' | 'pending' | 'claimed' | 'resolved'
  assigned_to: string | null
  human_replies: { sequence: number; text: string; time: string; agent_name: string }[]
}

const aiServiceUrl = (import.meta.env.VITE_AI_SERVICE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function testQQMailbox(
  email: string,
  authorizationCode: string,
): Promise<QQMailboxTestResult> {
  let response: Response
  try {
    response = await fetch(`${aiServiceUrl}/v1/mailboxes/qq/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, authorization_code: authorizationCode }),
    })
  } catch {
    throw new Error('无法连接本机邮箱服务，请确认 AI 服务已启动。')
  }

  const payload = await response.json().catch(() => null) as { detail?: string } | QQMailboxTestResult | null
  if (!response.ok) {
    throw new Error(payload && 'detail' in payload && payload.detail ? payload.detail : 'QQ 邮箱连接验证失败，请稍后重试。')
  }
  return payload as QQMailboxTestResult
}

export async function syncQQMailbox(
  email: string,
  authorizationCode: string,
  afterUid: number,
  mailboxId: string,
  storeId: string,
): Promise<QQMailboxSyncResult> {
  let response: Response
  try {
    response = await fetch(`${aiServiceUrl}/v1/mailboxes/qq/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, authorization_code: authorizationCode, after_uid: afterUid, limit: 10, mailbox_id: mailboxId, store_id: storeId }),
    })
  } catch {
    throw new Error('无法连接本机邮箱服务，新邮件同步暂时中断。')
  }
  const payload = await response.json().catch(() => null) as { detail?: string } | QQMailboxSyncResult | null
  if (!response.ok) {
    throw new Error(payload && 'detail' in payload && payload.detail ? payload.detail : 'QQ 邮箱同步失败，请稍后重试。')
  }
  return payload as QQMailboxSyncResult
}

export async function sendQQMailboxReply(
  email: string,
  authorizationCode: string,
  uid: number,
  text: string,
): Promise<{ sent: boolean; recipient: string; subject: string }> {
  let response: Response
  try {
    response = await fetch(`${aiServiceUrl}/v1/mailboxes/qq/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, authorization_code: authorizationCode, uid, text }),
    })
  } catch {
    throw new Error('无法连接邮箱发送服务，请稍后重试。')
  }
  const payload = await response.json().catch(() => null) as { detail?: string; sent?: boolean; recipient?: string; subject?: string } | null
  if (!response.ok) {
    throw new Error(payload?.detail || 'QQ 邮箱回复发送失败，请稍后重试。')
  }
  return payload as { sent: boolean; recipient: string; subject: string }
}

export async function publishLocalMailboxConversations(
  messages: LocalMailboxConversation[],
): Promise<void> {
  if (!messages.length) return
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/local/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  })
  if (!response.ok) throw new Error('无法共享本机邮件会话。')
}

export async function getLocalMailboxConversations(): Promise<LocalMailboxConversation[]> {
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/local/conversations`)
  if (!response.ok) throw new Error('无法读取本机邮件会话。')
  return response.json() as Promise<LocalMailboxConversation[]>
}

export async function publishLocalMailboxAccounts(accounts: LocalMailboxAccount[]): Promise<void> {
  if (!accounts.length) return
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/local/accounts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accounts }),
  })
  if (!response.ok) throw new Error('无法共享本机邮箱状态。')
}

export async function getLocalMailboxAccounts(): Promise<LocalMailboxAccount[]> {
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/local/accounts`)
  if (!response.ok) throw new Error('无法读取本机邮箱状态。')
  return response.json() as Promise<LocalMailboxAccount[]>
}

export async function getStorefrontConversations(): Promise<StorefrontConversation[]> {
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/storefront/conversations`)
  if (!response.ok) throw new Error('无法读取商城在线会话。')
  return response.json() as Promise<StorefrontConversation[]>
}

export async function updateStorefrontHandoff(
  conversationId: string,
  status: 'pending' | 'claimed' | 'resolved',
  assignedTo?: string,
): Promise<StorefrontConversation> {
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/storefront/conversations/${encodeURIComponent(conversationId)}/handoff`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, assigned_to: assignedTo }),
  })
  if (!response.ok) throw new Error('人工接管状态保存失败，请稍后重试。')
  return response.json() as Promise<StorefrontConversation>
}

export async function sendStorefrontConversationReply(
  conversationId: string,
  text: string,
  agentName = 'NOVA 客服',
): Promise<StorefrontConversation> {
  const response = await fetch(`${aiServiceUrl}/v1/mailboxes/storefront/conversations/${encodeURIComponent(conversationId)}/replies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, agent_name: agentName }),
  })
  if (!response.ok) throw new Error('人工回复发送失败，请稍后重试。')
  return response.json() as Promise<StorefrontConversation>
}
