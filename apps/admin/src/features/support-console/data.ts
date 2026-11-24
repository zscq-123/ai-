export type Page = 'analytics' | 'overview' | 'inbox' | 'reviews' | 'stores' | 'mailboxes' | 'knowledge' | 'ai'
export type Store = { id: string; name: string; platform: string; region: string; domain: string; url: string; color: string; status: 'connected' | 'attention'; ai: boolean; synced: string }
export type Mailbox = { id: string; email: string; provider: string; storeId: string; enabled: boolean; connection?: 'demo' | 'imap-verified'; messages?: number; unread?: number; lastUid?: number }
export type Message = { id: string; name: string; initials: string; storeId: string; channel: 'chat' | 'email'; subject: string; preview: string; time: string; unread: boolean; urgent: boolean; status: 'open' | 'resolved'; color: string; mailboxId?: string; mailboxUid?: number; senderEmail?: string; sourceMessageId?: string; handoffStatus?: 'none' | 'pending' | 'claimed' | 'resolved'; assignedTo?: string; messages: { role: 'customer' | 'agent'; text: string; time: string }[] }
export type Review = { id: string; name: string; initials: string; storeId: string; rating: number; product: string; text: string; date: string; reply?: string; color: string }
export type State = { messageDrafts?: Record<string, string>; reviewDrafts?: Record<string, string>; stores: Store[]; mailboxes: Mailbox[]; messages: Message[]; reviews: Review[] }
export const chungYipStoreUrl = (import.meta.env.VITE_CHUNGYIP_STORE_URL || 'https://154.36.185.46:18083').replace(/\/$/, '')
export const chungYipStore: Store = {
  id: 'chungyip',
  name: 'CHUNG YIP 健康产品商城',
  platform: '独立站',
  region: '新加坡 · 中文 / 英语',
  domain: chungYipStoreUrl.replace(/^https?:\/\//, ''),
  url: chungYipStoreUrl,
  color: 'blue',
  status: 'connected',
  ai: true,
  synced: '刚刚',
}
const legacyStoreIds = new Set(['s1', 's2', 's3', 's4'])
export const normalizeStoreId = (storeId: string) => legacyStoreIds.has(storeId) ? chungYipStore.id : storeId
export const initialState: State = {
  stores: [chungYipStore],
  mailboxes: [],
  messages: [],
  reviews: [],
}
export const pageNames: Record<Page, string> = { analytics: '数据中心', overview: '客服工作台', inbox: '会话', reviews: '评价管理', stores: '店铺管理', mailboxes: '邮箱接入', knowledge: '知识库', ai: 'Agent 管理' }
export const storageKey = 'nova-support-prototype-v1'
export function readState(): State {
  try {
    const s = JSON.parse(localStorage.getItem(storageKey) || 'null')
    if (s && Array.isArray(s.stores) && Array.isArray(s.messages) && Array.isArray(s.reviews) && Array.isArray(s.mailboxes)) {
      const additionalStores = (s.stores as Store[])
        .filter(store => !legacyStoreIds.has(store.id) && store.id !== chungYipStore.id && !store.domain.endsWith('.example'))
        .map(store => ({ ...store, url: store.url || `https://${store.domain}` }))
      return {
        stores: [chungYipStore, ...additionalStores],
        mailboxes: (s.mailboxes as Mailbox[])
          .filter(mailbox => mailbox.connection === 'imap-verified')
          .map(mailbox => ({ ...mailbox, storeId: normalizeStoreId(mailbox.storeId) })),
        messages: (s.messages as Message[])
          .filter(message => message.id.startsWith('qq-') || message.id.startsWith('storefront-'))
          .map(message => ({ ...message, storeId: normalizeStoreId(message.storeId) })),
        reviews: [],
        messageDrafts: {},
        reviewDrafts: {},
      }
    }
  } catch { /* A restricted browser can still use the in-memory prototype. */ }
  return structuredClone(initialState)
}
