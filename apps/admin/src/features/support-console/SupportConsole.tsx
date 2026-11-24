import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Button as FluentButton, Switch } from '@fluentui/react-components'
import { Icon } from './Icon'
import type { IconName } from './Icon'
import { initialState, normalizeStoreId, pageNames, readState, storageKey } from './data'
import type { Mailbox, Message, Page, Review, State, Store } from './data'
import './support-console.css'
import AnalyticsPage from './AnalyticsPage'
import { createAgentSkill, generateAgentDraft, getAgentConfiguration, updateAgentConfiguration, updateAgentSkill } from './agentApi'
import type { AgentConfiguration, AgentCostMode, AgentSkill, AgentTone } from './agentApi'
import { getLocalMailboxAccounts, getLocalMailboxConversations, getStorefrontConversations, publishLocalMailboxAccounts, publishLocalMailboxConversations, sendQQMailboxReply, sendStorefrontConversationReply, syncQQMailbox, testQQMailbox, updateStorefrontHandoff } from './mailboxApi'
import type { LocalMailboxAccount, LocalMailboxConversation, QQSyncedMessage, StorefrontConversation } from './mailboxApi'
import { getConnectedKnowledge, getKnowledgeDocument, getKnowledgeDocuments, setKnowledgeDocumentEnabled, uploadKnowledgeDocument } from './knowledgeApi'
import type { ConnectedKnowledgeItem, KnowledgeCategory, KnowledgeDocument } from './knowledgeApi'

type Modal = { type: 'store' | 'mail' | 'settings' | 'help' } | { type: 'detail' | 'mail-sync'; id: string }
type MailboxSession = { email: string; storeId: string; lastUid: number; active: boolean; lastSync?: string; error?: string }
type ConsoleContext = { data: State; update: (fn: (s: State) => State) => void; notify: (text: string) => void; navigate: (p: Page) => void; scope: string; query: string; open: (m: Modal) => void; messageId: string; inspectStore: (id: string) => void; openMessage: (id: string) => void; mailboxSessions: Record<string, MailboxSession>; startMailboxSync: (mailboxId: string, email: string, storeId: string, authorizationCode: string, lastUid: number) => void; stopMailboxSync: (mailboxId: string) => void; syncMailboxNow: (mailboxId: string) => Promise<void>; sendMailboxReply: (message: Message, text: string) => Promise<void> }
const Context = createContext<ConsoleContext>(null!)
const useConsole = () => useContext(Context)
const uid = () => crypto.randomUUID()
const now = () => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' })
function Button({ children, icon, onClick, primary = false, className = '', disabled = false, type = 'button' }: { children?: ReactNode; icon?: IconName; onClick?: () => void; primary?: boolean; className?: string; disabled?: boolean; type?: 'button' | 'submit' }) {
  return <FluentButton type={type} appearance={primary ? 'primary' : 'secondary'} className={`nc-btn ${primary ? 'primary' : ''} ${className}`} icon={icon ? <Icon name={icon} size={16} /> : undefined} onClick={onClick} disabled={disabled}>{children}</FluentButton>
}
function Badge({ children, tone = 'green' }: { children: ReactNode; tone?: string }) { return <span className={`nc-badge ${tone}`}><i />{children}</span> }
function Avatar({ text, color = 'green' }: { text: string; color?: string }) { return <span className={`nc-avatar ${color}`}>{text}</span> }
function Platform({ platform, color, small = false }: { platform: string; color: string; small?: boolean }) { return <span className={`nc-platform ${color} ${small ? 'small' : ''}`}>{platform === 'Shopify' ? <span className="shopify-letter">S</span> : platform === 'Lazada' ? 'L' : platform === 'TikTok Shop' ? '♪' : <Icon name="store" size={small ? 17 : 23} />}</span> }
function Toggle({ value, onChange, label }: { value: boolean; onChange: () => void; label: string }) { return <Switch className="nc-toggle" checked={value} aria-label={label} onChange={() => onChange()} /> }
function Empty({ title = '暂无匹配内容', text = '没有符合条件的内容，试试调整筛选条件。' }: { title?: string; text?: string }) { return <div className="nc-empty"><span><Icon name="inbox" size={28} /></span><h3>{title}</h3><p>{text}</p></div> }
function PageTitle({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) { return <div className="nc-page-title"><div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div><div className="nc-actions">{children}</div></div> }
function ModuleStats({ items }: { items: { label: string; value: string | number; hint: string; icon: IconName; tone?: string }[] }) { return <section className="nc-module-stats" aria-label="模块概览">{items.map(item => <div className={`nc-module-stat ${item.tone || ''}`} key={item.label}><span><Icon name={item.icon} size={18} /></span><div><small>{item.label}</small><strong>{item.value}</strong><p>{item.hint}</p></div></div>)}</section> }
function Tabs({ items, value, onChange, className = '', label = '页面筛选' }: { items: { id: string; label: string; count?: number }[]; value: string; onChange: (s: string) => void; className?: string; label?: string }) {
  return <div className={`nc-stable-tabs ${className}`.trim()} role="tablist" aria-label={label}>{items.map(item => <button type="button" role="tab" aria-selected={value === item.id} className={value === item.id ? 'active' : ''} key={item.id} onClick={() => onChange(item.id)}><span className="nc-stable-tab-label">{item.label}</span>{item.count !== undefined && <span className="nc-stable-tab-count">{item.count}</span>}</button>)}</div>
}
function storeMatch(storeId: string, scope: string) { return scope === 'all' || storeId === scope }

function mailboxMessage(item: QQSyncedMessage, storeId: string, mailboxId: string): Message {
  const received = item.received_at ? new Date(item.received_at) : new Date()
  const validDate = !Number.isNaN(received.getTime())
  const time = validDate ? received.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' }) : now()
  const body = item.text.trim() || '（邮件正文为空）'
  const name = item.sender_name || item.sender_email || 'QQ 邮箱客户'
  const initials = [...name].slice(0, 2).join('').toUpperCase()
  return { id: `qq-${mailboxId}-${item.uid}`, name, initials, storeId, channel: 'email', subject: item.subject || '（无主题）', preview: body.slice(0, 120), time, unread: true, urgent: false, status: 'open', color: 'blue', mailboxId, mailboxUid: item.uid, senderEmail: item.sender_email, sourceMessageId: item.message_id, messages: [{ role: 'customer', text: body, time }] }
}

function sharedMailboxMessage(item: LocalMailboxConversation): Message {
  return { id: item.id, name: item.name, initials: item.initials, storeId: normalizeStoreId(item.store_id), channel: 'email', subject: item.subject, preview: item.preview, time: item.time, unread: item.unread, urgent: item.urgent, status: 'open', color: item.color, mailboxId: item.mailbox_id || undefined, mailboxUid: item.mailbox_uid || undefined, senderEmail: item.sender_email || undefined, sourceMessageId: item.message_id || undefined, messages: [{ role: 'customer', text: item.text, time: item.time }] }
}

function sharedStorefrontConversation(item: StorefrontConversation): Message {
  return { id: item.id, name: item.name, initials: item.initials, storeId: normalizeStoreId(item.store_id), channel: 'chat', subject: item.subject, preview: item.preview, time: item.time, unread: item.unread, urgent: item.urgent, status: item.status, color: item.color, handoffStatus: item.handoff_status, assignedTo: item.assigned_to || undefined, messages: item.messages }
}

function localMailboxConversation(message: Message): LocalMailboxConversation {
  return { id: message.id, name: message.name, initials: message.initials, store_id: message.storeId, subject: message.subject, preview: message.preview, time: message.time, unread: message.unread, urgent: message.urgent, color: message.color, text: message.messages.find(item => item.role === 'customer')?.text ?? message.preview, mailbox_id: message.mailboxId, mailbox_uid: message.mailboxUid, sender_email: message.senderEmail, message_id: message.sourceMessageId }
}

function localMailboxAccount(mailbox: Mailbox): LocalMailboxAccount {
  return { id: mailbox.id, email: mailbox.email, provider: mailbox.provider, store_id: mailbox.storeId, enabled: mailbox.enabled, connection: 'imap-verified', messages: mailbox.messages ?? 0, unread: mailbox.unread ?? 0, last_uid: mailbox.lastUid ?? 0 }
}

function sharedMailboxAccount(account: LocalMailboxAccount): Mailbox {
  return { id: account.id, email: account.email, provider: account.provider, storeId: normalizeStoreId(account.store_id), enabled: account.enabled, connection: account.connection, messages: account.messages, unread: account.unread, lastUid: account.last_uid }
}

export default function SupportConsole() {
  const [data, setData] = useState<State>(readState)
  const dataRef = useRef(data)
  const [page, setPage] = useState<Page>(() => { const hash = location.hash.slice(1); return hash in pageNames ? hash as Page : 'overview' })
  const [scope, setScope] = useState('all')
  const [messageId, setMessageId] = useState('m1')
  const [query, setQuery] = useState('')
  const [modal, setModal] = useState<Modal | null>(null)
  const [toast, setToast] = useState('')
  const [mobile, setMobile] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const searchRef = useRef<HTMLInputElement>(null)
  const mailboxSecrets = useRef<Record<string, string>>({})
  const mailboxSessionRef = useRef<Record<string, MailboxSession>>({})
  const mailboxSyncLocks = useRef(new Set<string>())
  const [mailboxSessions, setMailboxSessions] = useState<Record<string, MailboxSession>>({})
  const notify = (text: string) => { setToast(text); clearTimeout(timer.current); timer.current = setTimeout(() => setToast(''), 4200) }
  const navigate = (p: Page) => { setPage(p); window.history.pushState(null, '', `#${p}`); setQuery(''); setMobile(false) }
  const updateMailboxSessions = (fn: (current: Record<string, MailboxSession>) => Record<string, MailboxSession>) => {
    const next = fn(mailboxSessionRef.current)
    mailboxSessionRef.current = next
    setMailboxSessions(next)
  }
  const syncMailboxNow = async (mailboxId: string) => {
    const session = mailboxSessionRef.current[mailboxId]
    const authorizationCode = mailboxSecrets.current[mailboxId]
    if (!session?.active || !authorizationCode || mailboxSyncLocks.current.has(mailboxId)) return
    mailboxSyncLocks.current.add(mailboxId)
    try {
      const result = await syncQQMailbox(session.email, authorizationCode, session.lastUid, mailboxId, session.storeId)
      const incoming = result.messages.map(item => mailboxMessage(item, session.storeId, mailboxId)).reverse()
      const added = incoming.length
      await publishLocalMailboxConversations(incoming.map(localMailboxConversation)).catch(() => undefined)
      setData(current => {
        const existingIds = new Set(current.messages.map(message => message.id))
        const fresh = incoming.filter(message => !existingIds.has(message.id))
        return {
          ...current,
          messages: [...fresh, ...current.messages],
          mailboxes: current.mailboxes.map(mailbox => mailbox.id === mailboxId ? {
            ...mailbox,
            enabled: true,
            lastUid: result.last_uid,
            messages: (mailbox.messages ?? 0) + fresh.length,
            unread: (mailbox.unread ?? 0) + fresh.length,
          } : mailbox),
        }
      })
      updateMailboxSessions(current => ({ ...current, [mailboxId]: { ...session, lastUid: result.last_uid, lastSync: now(), error: '' } }))
      if (added > 0) notify(`已从 QQ 邮箱同步 ${added} 封新邮件，并加入客服会话`)
    } catch (caught) {
      const error = caught instanceof Error ? caught.message : 'QQ 邮箱同步失败，请稍后重试。'
      updateMailboxSessions(current => ({ ...current, [mailboxId]: { ...session, error } }))
    } finally {
      mailboxSyncLocks.current.delete(mailboxId)
    }
  }
  const startMailboxSync = (mailboxId: string, email: string, storeId: string, authorizationCode: string, lastUid: number) => {
    mailboxSecrets.current[mailboxId] = authorizationCode
    const session: MailboxSession = { email, storeId, lastUid, active: true }
    updateMailboxSessions(current => ({ ...current, [mailboxId]: session }))
    queueMicrotask(() => void syncMailboxNow(mailboxId))
  }
  const stopMailboxSync = (mailboxId: string) => {
    delete mailboxSecrets.current[mailboxId]
    updateMailboxSessions(current => current[mailboxId] ? ({ ...current, [mailboxId]: { ...current[mailboxId], active: false } }) : current)
  }
  const sendMailboxReply = async (message: Message, text: string) => {
    const mailbox = dataRef.current.mailboxes.find(item => item.id === message.mailboxId || message.id.startsWith(`qq-${item.id}-`))
    if (!mailbox || mailbox.provider !== 'QQ 邮箱') throw new Error('这封邮件没有关联可发送的 QQ 邮箱。')
    const session = mailboxSessionRef.current[mailbox.id]
    const authorizationCode = mailboxSecrets.current[mailbox.id]
    if (!session?.active || !authorizationCode) throw new Error('请先在“邮箱接入”中重新启动 QQ 邮箱同步，再发送回复。')
    const uidText = message.id.startsWith(`qq-${mailbox.id}-`) ? message.id.slice(`qq-${mailbox.id}-`.length) : ''
    const uid = message.mailboxUid || (/^\d+$/.test(uidText) ? Number(uidText) : 0)
    if (!uid) throw new Error('无法识别原邮件，请重新同步邮箱后再发送。')
    await sendQQMailboxReply(mailbox.email, authorizationCode, uid, text)
  }
  useEffect(() => { document.title = 'NOVA · AI 客服工作台'; const onHash = () => { const p = location.hash.slice(1); if (p in pageNames) { setPage(p as Page); setQuery('') } }; const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); searchRef.current?.focus() } }; window.addEventListener('hashchange', onHash); window.addEventListener('popstate', onHash); window.addEventListener('keydown', onKey); return () => { window.removeEventListener('hashchange', onHash); window.removeEventListener('popstate', onHash); window.removeEventListener('keydown', onKey); clearTimeout(timer.current) } }, [])
  useEffect(() => { dataRef.current = data }, [data])
  useEffect(() => {
    const interval = window.setInterval(() => {
      Object.entries(mailboxSessionRef.current).forEach(([mailboxId, session]) => {
        if (session.active) void syncMailboxNow(mailboxId)
      })
    }, 60_000)
    return () => {
      window.clearInterval(interval)
      mailboxSecrets.current = {}
    }
  }, [])
  useEffect(() => {
    let active = true
    const refreshSharedMailboxState = async () => {
      const localConversations = dataRef.current.messages.filter(message => message.id.startsWith('qq-')).map(localMailboxConversation)
      const localAccounts = dataRef.current.mailboxes.filter(mailbox => mailbox.connection === 'imap-verified').map(localMailboxAccount)
      await Promise.all([
        publishLocalMailboxConversations(localConversations).catch(() => undefined),
        publishLocalMailboxAccounts(localAccounts).catch(() => undefined),
      ])
      const [sharedConversations, sharedAccounts, storefrontConversations] = await Promise.all([
        getLocalMailboxConversations().catch(() => []),
        getLocalMailboxAccounts().catch(() => []),
        getStorefrontConversations().catch(() => []),
      ])
      if (!active || (!sharedConversations.length && !sharedAccounts.length && !storefrontConversations.length)) return
      setData(current => {
        const existingIds = new Set(current.messages.map(message => message.id))
        const freshMail = sharedConversations.filter(message => !existingIds.has(message.id)).map(sharedMailboxMessage)
        const storefront = storefrontConversations.map(sharedStorefrontConversation)
        const storefrontById = new Map(storefront.map(message => [message.id, message]))
        const refreshed = current.messages.map(message => {
          const incoming = storefrontById.get(message.id)
          if (!incoming) return message
          return { ...incoming, unread: incoming.messages.length > message.messages.length ? true : message.unread }
        })
        const freshStorefront = storefront.filter(message => !existingIds.has(message.id))
        const accounts = new Map(current.mailboxes.map(mailbox => [mailbox.id, mailbox]))
        sharedAccounts.forEach(account => accounts.set(account.id, { ...accounts.get(account.id), ...sharedMailboxAccount(account) }))
        const fresh = [...freshStorefront, ...freshMail]
        return { ...current, messages: fresh.length ? [...fresh, ...refreshed] : refreshed, mailboxes: [...accounts.values()] }
      })
    }
    void refreshSharedMailboxState()
    const interval = window.setInterval(() => void refreshSharedMailboxState(), 5_000)
    return () => { active = false; window.clearInterval(interval) }
  }, [])
  useEffect(() => { try { localStorage.setItem(storageKey, JSON.stringify({ ...data, messageDrafts: {} })) } catch { queueMicrotask(() => notify('浏览器存储不可用，本次演示仍可继续；刷新后会恢复初始数据。')) } }, [data])
  const unread = data.messages.filter(m => m.unread && storeMatch(m.storeId, scope)).length
  const pending = data.reviews.filter(r => !r.reply && storeMatch(r.storeId, scope)).length
  const nav = (p: Page, icon: IconName, label: string, count?: number) => <button key={p} className={`nc-nav-item ${page === p ? 'selected' : ''}`} onClick={() => navigate(p)} aria-current={page === p ? 'page' : undefined}><Icon name={icon} /><span>{label}</span>{!!count && <b>{count > 99 ? '99+' : count}</b>}</button>
  return <Context.Provider value={{ data, update: setData, notify, navigate, scope, query, open: setModal, messageId, inspectStore: id => { setScope(id); navigate('analytics') }, openMessage: id => { setMessageId(id); setData(d => ({ ...d, messages: d.messages.map(m => m.id === id ? { ...m, unread: false } : m) })); navigate('inbox') }, mailboxSessions, startMailboxSync, stopMailboxSync, syncMailboxNow, sendMailboxReply }}><div className="nc-app">
    {mobile && <button className="nc-mobile-scrim" aria-label="关闭导航" onClick={() => setMobile(false)} />}
    <aside className={`nc-sidebar ${mobile ? 'expanded' : ''}`}>
      <a className="nc-brand" href="#overview" onClick={() => navigate('overview')}><span className="nc-brand-mark"><Icon name="spark" size={19} /></span><strong>NOVA</strong><small className="nc-online"><i />在线</small></a>
      <div className="nc-nav-label">服务空间</div><nav aria-label="服务空间">{nav('overview', 'grid', '客服工作台')}{nav('inbox', 'chat', '会话', unread)}{nav('reviews', 'star', '评价管理', pending)}{nav('analytics', 'trend', '数据中心')}</nav>
      <div className="nc-nav-label">运营管理</div><nav aria-label="运营管理">{nav('ai', 'spark', 'Agent 管理')}{nav('knowledge', 'file', '知识库')}{nav('stores', 'store', '店铺管理')}{nav('mailboxes', 'mail', '邮箱接入')}</nav>
      <div className="nc-sidebar-bottom"><button className="nc-nav-item" onClick={() => setModal({ type: 'help' })}><Icon name="help" /><span>使用说明</span></button><button className="nc-profile" onClick={() => setModal({ type: 'settings' })}><Avatar text="N" color="dark" /><span><strong>NOVA 管理员</strong><small>AI 客服空间</small></span><Icon name="settings" size={18} /></button></div>
    </aside>
    <main data-page={page} className={`nc-main is-duoke ${page === 'overview' ? 'is-workbench' : 'is-console-page'}`}><header className="nc-topbar is-duoke"><div className="nc-breadcrumb"><button className="nc-icon-btn nc-menu" aria-label="展开导航" onClick={() => setMobile(!mobile)}><Icon name="menu" /></button><span>AI 客服中心</span><Icon name="chevron" size={12} /><strong>{pageNames[page]}</strong></div><div className="nc-top-actions"><label className="nc-store-select"><Icon name="store" size={15} /><select aria-label="当前店铺范围" value={scope} onChange={e => setScope(e.target.value)}><option value="all">全部店铺</option>{data.stores.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label className="nc-global-search"><Icon name="search" size={16} /><input ref={searchRef} aria-label="搜索当前页面" placeholder={page === 'overview' ? '搜索客户会话' : page === 'analytics' ? '搜索店铺' : page === 'knowledge' ? '搜索知识内容' : '搜索当前页面'} value={query} onChange={e => { if (page === 'overview') { setPage('inbox'); window.history.pushState(null, '', '#inbox') } setQuery(e.target.value) }} /><kbd>⌘ K</kbd></label><button className="nc-icon-btn nc-language" aria-label="切换语言" onClick={() => notify('当前界面语言：简体中文')}>中</button><button className="nc-icon-btn nc-notification" aria-label="查看提醒" onClick={() => navigate('overview')}><Icon name="bell" size={17} />{unread + pending > 0 && <i />}</button></div></header>
      <div className={`nc-content ${page === 'overview' ? 'nc-workbench-content' : 'nc-console-content'}`}>
        {page === 'overview' && <Overview />}{page === 'analytics' && <AnalyticsPage stores={data.stores} scope={scope} query={query} onSelectStore={setScope} onConnectData={() => navigate('stores')} />}{page === 'stores' && <Stores />}{page === 'mailboxes' && <Mailboxes />}{page === 'knowledge' && <Knowledge />}{page === 'inbox' && <Inbox />}{page === 'reviews' && <Reviews />}{page === 'ai' && <Assistant />}
      </div>
    </main>
    {modal && <ModalHost modal={modal} close={() => setModal(null)} reset={() => { setData(structuredClone(initialState)); setScope('all'); setQuery(''); notify('演示数据已恢复') }} />}
    <div className={`nc-toast ${toast ? 'visible' : ''}`} role="status" aria-live="polite"><Icon name="check" size={17} />{toast}</div>
  </div></Context.Provider>
}

function Overview() {
  const { data, scope, navigate, notify, open, openMessage, mailboxSessions } = useConsole()
  const [tab, setTab] = useState<'conversations' | 'reviews' | 'stores' | 'mailboxes'>('conversations')
  const [status, setStatus] = useState<'pending' | 'done'>('pending')
  const [search, setSearch] = useState('')
  const [filterOpen, setFilterOpen] = useState(false)
  const stores = data.stores.filter(s => storeMatch(s.id, scope))
  const scopedMessages = data.messages.filter(m => storeMatch(m.storeId, scope))
  const scopedReviews = data.reviews.filter(r => storeMatch(r.storeId, scope))
  const mailboxes = data.mailboxes.filter(m => storeMatch(m.storeId, scope))
  const messages = scopedMessages.filter(m => m.status === 'open')
  const reviews = scopedReviews.filter(r => !r.reply)
  const attention = stores.filter(s => s.status === 'attention')
  const pausedMailboxes = mailboxes.filter(m => !m.enabled)
  const resolved = scopedMessages.filter(m => m.status === 'resolved')
  const repliedReviews = scopedReviews.filter(r => r.reply)
  const aiReceiving = messages.filter(message => data.stores.find(store => store.id === message.storeId)?.ai)
  const responseSamples = scopedMessages.flatMap(message => {
    const firstCustomer = message.messages.find(item => item.role === 'customer')
    const firstAgent = message.messages.find(item => item.role === 'agent')
    if (!firstCustomer || !firstAgent) return []
    const [customerHour, customerMinute] = firstCustomer.time.split(':').map(Number)
    const [agentHour, agentMinute] = firstAgent.time.split(':').map(Number)
    const seconds = ((agentHour * 60 + agentMinute) - (customerHour * 60 + customerMinute)) * 60
    return seconds >= 0 ? [seconds] : []
  })
  const averageResponse = responseSamples.length ? Math.round(responseSamples.reduce((sum, value) => sum + value, 0) / responseSamples.length) : null
  const metrics: { label: string; value: string | number; tone: string; icon: IconName; action: () => void }[] = [
    { label: '待处理会话', value: messages.length, tone: 'red', icon: 'inbox', action: () => navigate('inbox') },
    { label: 'AI 接待中会话', value: aiReceiving.length, tone: 'dark', icon: 'chat', action: () => navigate('inbox') },
    { label: 'AI 解决会话数', value: resolved.length, tone: 'dark', icon: 'check', action: () => navigate('inbox') },
    { label: '今日会话平均响应', value: averageResponse === null ? '—' : averageResponse < 60 ? `${averageResponse}s` : `${Math.round(averageResponse / 60)}m`, tone: 'green', icon: 'clock', action: () => navigate('analytics') },
  ]
  const tabs = [
    { id: 'conversations' as const, label: '待处理会话', pending: messages.length, done: resolved.length },
    { id: 'reviews' as const, label: '评价管理', pending: reviews.length, done: repliedReviews.length },
    { id: 'stores' as const, label: '店铺异常', pending: attention.length, done: stores.length - attention.length },
    { id: 'mailboxes' as const, label: '邮箱同步', pending: pausedMailboxes.length, done: mailboxes.length - pausedMailboxes.length },
  ]
  const activeTab = tabs.find(item => item.id === tab)!
  const normalizedSearch = search.trim().toLowerCase()
  const filteredMessages = scopedMessages.filter(message => (status === 'pending' ? message.status === 'open' : message.status === 'resolved') && `${message.name} ${message.subject} ${message.preview}`.toLowerCase().includes(normalizedSearch))
  const filteredReviews = scopedReviews.filter(review => (status === 'pending' ? !review.reply : !!review.reply) && `${review.name} ${review.product} ${review.text}`.toLowerCase().includes(normalizedSearch))
  const filteredStores = stores.filter(store => (status === 'pending' ? store.status === 'attention' : store.status === 'connected') && `${store.name} ${store.platform} ${store.domain}`.toLowerCase().includes(normalizedSearch))
  const filteredMailboxes = mailboxes.filter(mailbox => (status === 'pending' ? !mailbox.enabled : mailbox.enabled) && `${mailbox.email} ${mailbox.provider}`.toLowerCase().includes(normalizedSearch))
  const currentCount = tab === 'conversations' ? filteredMessages.length : tab === 'reviews' ? filteredReviews.length : tab === 'stores' ? filteredStores.length : filteredMailboxes.length
  const listColumns = tab === 'conversations'
    ? ['客户与来源', '会话主题', '最新消息', '时间与状态']
    : tab === 'reviews'
      ? ['客户与店铺', '评价商品', '评价内容', '日期与状态']
      : tab === 'stores'
        ? ['店铺', '域名', '连接说明', '同步与操作']
        : ['服务邮箱', '关联店铺', '同步说明', '状态与操作']
  const exportCurrent = () => {
    const rows = tab === 'conversations' ? filteredMessages.map(item => [item.name, item.subject, item.status, item.time]) : tab === 'reviews' ? filteredReviews.map(item => [item.name, item.product, `${item.rating} 星`, item.reply ? '已回复' : '待回复']) : tab === 'stores' ? filteredStores.map(item => [item.name, item.platform, item.status, item.synced]) : filteredMailboxes.map(item => [item.email, item.provider, item.enabled ? '同步中' : '已暂停', data.stores.find(store => store.id === item.storeId)?.name || ''])
    const csv = ['名称,主题或平台,状态,时间或店铺', ...rows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(','))].join('\n')
    const href = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = href
    anchor.download = `nova-${tab}-${status}.csv`
    anchor.click()
    URL.revokeObjectURL(href)
    notify(`已导出 ${rows.length} 条当前演示数据`)
  }
  const noResults = currentCount === 0
  return <div className="nc-workbench">
    <section className="nc-workbench-board">
      <div className="nc-workbench-heading"><span><Icon name="spark" size={17} /></span><div><h1>会话数据看板</h1><p>实时查看需要人工跟进的客户服务数据</p></div><button onClick={() => navigate('analytics')}>查看趋势<Icon name="chevron" size={13} /></button></div>
      <div className="nc-workbench-kpis">{metrics.map(metric => <button key={metric.label} onClick={metric.action}><span><Icon name={metric.icon} size={22} /></span><div><small>{metric.label}</small><strong className={metric.tone}>{metric.value}</strong></div></button>)}</div>
    </section>
    <section className="nc-workbench-tasks">
      <div className="nc-workbench-tabs" role="tablist">{tabs.map(item => <button role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} key={item.id} onClick={() => { setTab(item.id); setSearch(''); setFilterOpen(false) }}>{item.label}<b>{item.pending}</b></button>)}</div>
      <div className="nc-workbench-toolbar">
        <div className="nc-workbench-status"><button className={status === 'pending' ? 'active' : ''} onClick={() => setStatus('pending')}>待处理 <b>{activeTab.pending}</b></button><button className={status === 'done' ? 'active' : ''} onClick={() => setStatus('done')}>已处理 <b>{activeTab.done}</b></button></div>
        <label className="nc-workbench-search"><Icon name="search" size={15} /><input aria-label="搜索当前工作台" placeholder={tab === 'conversations' ? '搜索客户或会话主题' : tab === 'reviews' ? '搜索评价或商品' : '搜索店铺或账号'} value={search} onChange={event => setSearch(event.target.value)} /></label>
        <div className="nc-workbench-filter-wrap"><button className={`nc-workbench-filter ${filterOpen ? 'active' : ''}`} aria-expanded={filterOpen} aria-label="更多筛选" onClick={() => setFilterOpen(!filterOpen)}><Icon name="filter" size={16} /></button>{filterOpen && <div className="nc-workbench-filter-menu"><div><span>店铺范围</span><strong>{scope === 'all' ? '全部店铺' : data.stores.find(store => store.id === scope)?.name}</strong></div><div><span>当前业务</span><strong>{activeTab.label}</strong></div><div className="nc-workbench-filter-actions"><button onClick={() => { setSearch(''); setStatus('pending') }}>重置</button><button onClick={() => setFilterOpen(false)}>完成</button></div></div>}</div>
        <button className="nc-workbench-export" onClick={exportCurrent}>导出</button>
      </div>
      {noResults ? <Empty title={status === 'pending' ? '当前没有待处理事项' : '暂无已处理记录'} text="可以切换业务类型、处理状态或店铺范围查看其他内容。" /> : <div className="nc-workbench-list">
        <div className="nc-workbench-list-head" aria-hidden="true">{listColumns.map(column => <span key={column}>{column}</span>)}</div>
        {tab === 'conversations' && filteredMessages.map(message => <button className="nc-workbench-row" key={message.id} onClick={() => openMessage(message.id)}><div className="nc-workbench-row-head"><Avatar text={message.initials} color={message.color} /><span><strong>{message.name}</strong><small><Icon name={message.channel === 'email' ? 'mail' : 'chat'} size={12} />{data.stores.find(store => store.id === message.storeId)?.name}</small></span><Badge tone={message.urgent ? 'orange' : 'gray'}>{message.urgent ? '优先' : message.channel === 'email' ? '邮件' : '在线'}</Badge></div><h3>{message.subject}</h3><p>{message.preview}</p><footer><span><Icon name="clock" size={13} />{message.time}</span><span>{message.status === 'open' ? '待处理' : '已解决'}<Icon name="chevron" size={13} /></span></footer></button>)}
        {tab === 'reviews' && filteredReviews.map(review => <button className="nc-workbench-row" key={review.id} onClick={() => navigate('reviews')}><div className="nc-workbench-row-head"><Avatar text={review.initials} color={review.color} /><span><strong>{review.name}</strong><small><Icon name="store" size={12} />{data.stores.find(store => store.id === review.storeId)?.name}</small></span><span className="nc-workbench-stars">{'★'.repeat(review.rating)}<i>{'★'.repeat(5 - review.rating)}</i></span></div><h3>{review.product}</h3><p>{review.text}</p><footer><span><Icon name="clock" size={13} />{review.date}</span><span>{review.reply ? '已回复' : '待回复'}<Icon name="chevron" size={13} /></span></footer></button>)}
        {tab === 'stores' && filteredStores.map(store => <button className="nc-workbench-row" key={store.id} onClick={() => open({ type: 'detail', id: store.id })}><div className="nc-workbench-row-head"><Platform platform={store.platform} color={store.color} /><span><strong>{store.name}</strong><small>{store.platform} · {store.region}</small></span><Badge tone={store.status === 'connected' ? 'gray' : 'orange'}>{store.status === 'connected' ? '正常' : '需处理'}</Badge></div><h3>{store.domain}</h3><p>{store.status === 'connected' ? '店铺连接正常，消息与服务配置可继续使用。' : '店铺授权已过期，消息同步和 AI 接待已暂停。'}</p><footer><span><Icon name="clock" size={13} />{store.synced}</span><span>管理店铺<Icon name="chevron" size={13} /></span></footer></button>)}
        {tab === 'mailboxes' && filteredMailboxes.map(mailbox => <button className="nc-workbench-row" key={mailbox.id} onClick={() => navigate('mailboxes')}><div className="nc-workbench-row-head"><span className="nc-workbench-mail-icon"><Icon name="mail" size={20} /></span><span><strong>{mailbox.email}</strong><small>{mailbox.provider}</small></span><Badge tone={mailbox.enabled ? 'gray' : 'orange'}>{mailbox.connection === 'imap-verified' ? mailboxSessions[mailbox.id]?.active ? '自动同步中' : 'IMAP 已验证' : mailbox.enabled ? '演示同步' : '已暂停'}</Badge></div><h3>{data.stores.find(store => store.id === mailbox.storeId)?.name}</h3><p>{mailbox.connection === 'imap-verified' ? mailboxSessions[mailbox.id]?.active ? `已开启本机自动同步，每 60 秒检查新增邮件；邮箱共 ${mailbox.messages ?? 0} 封、未读 ${mailbox.unread ?? 0} 封。` : `QQ IMAP 登录已验证，邮箱共 ${mailbox.messages ?? 0} 封、未读 ${mailbox.unread ?? 0} 封；需重新输入授权码启动同步。` : mailbox.enabled ? '这是演示邮箱记录，未连接真实邮件服务器。' : '邮箱演示状态已暂停。'}</p><footer><span><Icon name="shield" size={13} />服务邮箱</span><span>管理邮箱<Icon name="chevron" size={13} /></span></footer></button>)}
      </div>}
    </section>
  </div>
}

function Stores() {
  const { data, update, notify, scope, query, open } = useConsole()
  const [filter, setFilter] = useState('all')
  const scopedStores = data.stores.filter(store => storeMatch(store.id, scope))
  const stores = data.stores.filter(s => storeMatch(s.id, scope) && `${s.name} ${s.platform} ${s.domain}`.toLowerCase().includes(query.toLowerCase()) && (filter === 'all' || s.status === filter))
  return <>
    <PageTitle title="店铺管理">
      <a className="nc-btn" href={data.stores[0]?.url} target="_blank" rel="noreferrer"><Icon name="link" size={16} />访问线上商城</a>
    </PageTitle>
    <ModuleStats items={[{ label: '店铺数量', value: scopedStores.length, hint: '当前空间内店铺', icon: 'store' }, { label: 'AI 接待中', value: scopedStores.filter(store => store.ai).length, hint: '自动处理客户咨询', icon: 'spark' }, { label: '需要处理', value: scopedStores.filter(store => store.status === 'attention').length, hint: '需要人工检查', icon: 'bell' }, { label: '关联邮箱', value: data.mailboxes.filter(mailbox => storeMatch(mailbox.storeId, scope)).length, hint: '接收客户邮件', icon: 'mail' }]} />
    <div className="nc-toolbar"><Tabs items={[{ id: 'all', label: '全部店铺' }, { id: 'connected', label: '连接正常' }, { id: 'attention', label: '需要处理' }]} value={filter} onChange={setFilter} /><span className="nc-muted">{stores.length} 家店铺</span></div>
    <section className="nc-panel nc-store-table"><div className="nc-store-table-head"><span>店铺</span><span>状态</span><span>AI 接待</span><span>最近同步</span><span /></div>{!stores.length ? <Empty /> : stores.map(s => <div className="nc-store-row" key={s.id}><div className="nc-store-identity"><Platform platform={s.platform} color={s.color} /><div><h2>{s.name}</h2><p>{s.platform} · {s.domain}</p></div></div><Badge tone={s.status === 'connected' ? 'gray' : 'orange'}>{s.status === 'connected' ? '正常' : '需处理'}</Badge><Toggle value={s.ai} label={`${s.name} AI 自动接待`} onChange={() => { if (s.status === 'attention') { open({ type: 'detail', id: s.id }); return } update(d => ({ ...d, stores: d.stores.map(a => a.id === s.id ? { ...a, ai: !a.ai } : a) })); notify(s.ai ? '该店铺已切换为人工接待' : '该店铺已开启 AI 接待') }} /><span className="nc-sync-time">{s.synced === '授权已过期' ? '已暂停' : s.synced}</span><div className="nc-store-actions"><a className="nc-text-button" href={s.url} target="_blank" rel="noreferrer">打开商城</a><Button onClick={() => open({ type: 'detail', id: s.id })}>{s.status === 'attention' ? '重新授权' : '管理'}</Button></div></div>)}</section>
  </>
}

function Mailboxes() {
  const { data, update, notify, scope, query, open, mailboxSessions, stopMailboxSync, syncMailboxNow } = useConsole()
  const scopedAccounts = data.mailboxes.filter(mailbox => storeMatch(mailbox.storeId, scope))
  const accounts = data.mailboxes.filter(m => storeMatch(m.storeId, scope) && `${m.email} ${m.provider}`.toLowerCase().includes(query.toLowerCase()))
  return <><PageTitle title="邮箱接入" subtitle="统一接入服务邮箱，把客户来信同步到会话工作台。"><Button primary icon="plus" onClick={() => open({ type: 'mail' })}>接入邮箱</Button></PageTitle><ModuleStats items={[{ label: '服务邮箱', value: scopedAccounts.length, hint: '统一承接多店铺客户来信', icon: 'mail' }, { label: '真实 IMAP', value: scopedAccounts.filter(account => account.connection === 'imap-verified').length, hint: '已完成本机连接验证', icon: 'shield' }, { label: '邮箱未读', value: scopedAccounts.reduce((total, account) => total + (account.unread ?? 0), 0), hint: '同步邮箱中的未读总量', icon: 'inbox' }, { label: '当前同步', value: Object.values(mailboxSessions).filter(session => session.active && storeMatch(session.storeId, scope)).length, hint: '当前页面保持授权的邮箱', icon: 'refresh' }]} /><div className="nc-section-heading"><h2>服务邮箱 <small>{accounts.length}</small></h2><span className="nc-muted">QQ 邮箱支持本机实时同步；其他服务商当前为演示接入</span></div><div className="nc-panel nc-account-list">{!accounts.length ? <Empty title="还没有接入邮箱" text="点击「接入邮箱」，为当前店铺添加服务邮箱。" /> : accounts.map(m => <div className="nc-mail-account" key={m.id}><span className="nc-provider"><Icon name="mail" /></span><div className="nc-mail-identity"><h3>{m.email}</h3><p>{m.provider}<span>·</span>{data.stores.find(s => s.id === m.storeId)?.name}{m.connection === 'imap-verified' && <><span>·</span>{m.messages ?? 0} 封邮件 / {m.unread ?? 0} 封未读{mailboxSessions[m.id]?.active && <><span>·</span>{mailboxSessions[m.id].error ? '同步需重试' : mailboxSessions[m.id].lastSync ? `最近同步 ${mailboxSessions[m.id].lastSync}` : '自动同步已开启'}</>}</>}</p></div><Badge tone={mailboxSessions[m.id]?.error ? 'orange' : m.enabled ? 'gray' : 'orange'}>{m.connection === 'imap-verified' ? mailboxSessions[m.id]?.active ? '自动同步中' : 'IMAP 已验证' : m.enabled ? '演示同步' : '已暂停'}</Badge>{m.connection === 'imap-verified' && <Button icon="refresh" onClick={() => { if (mailboxSessions[m.id]?.active) void syncMailboxNow(m.id); else open({ type: 'mail-sync', id: m.id }) }}>{mailboxSessions[m.id]?.active ? '立即同步' : '启动同步'}</Button>}<Toggle label={`${m.email} 本地启用状态`} value={m.enabled} onChange={() => { if (m.connection === 'imap-verified') { if (m.enabled) { stopMailboxSync(m.id); update(d => ({ ...d, mailboxes: d.mailboxes.map(a => a.id === m.id ? { ...a, enabled: false } : a) })); notify('已停止当前页面的 QQ 邮箱自动同步') } else open({ type: 'mail-sync', id: m.id }); return } update(d => ({ ...d, mailboxes: d.mailboxes.map(a => a.id === m.id ? { ...a, enabled: !a.enabled } : a) })); notify(m.enabled ? '已暂停该邮箱的演示状态' : '已恢复该邮箱的演示状态') }} /></div>)}</div></>
}

type KnowledgeViewEntry = {
  id: string
  title: string
  category: KnowledgeCategory
  source: string
  summary: string
  updatedAt: string
  kind: 'uploaded' | 'faq' | 'category' | 'product'
  status: 'ready' | 'needs_attention'
  enabled: boolean
  keywords?: string[]
  itemCount?: number | null
  document?: KnowledgeDocument
}

function Knowledge() {
  const { query, notify } = useConsole()
  const [tab, setTab] = useState('operations')
  const [entries, setEntries] = useState<KnowledgeDocument[]>([])
  const [connected, setConnected] = useState<ConnectedKnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState('')
  const [error, setError] = useState('')
  const [selectedEntry, setSelectedEntry] = useState<KnowledgeViewEntry | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    let active = true
    void Promise.all([getKnowledgeDocuments(), getConnectedKnowledge()]).then(([documents, connectedItems]) => { if (active) { setEntries(documents); setConnected(connectedItems) } }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : '无法读取知识库。') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
  const formatTime = (value: string) => new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' })
  const normalized = query.trim().toLowerCase()
  const knowledgeEntries: KnowledgeViewEntry[] = [
    ...connected.map(entry => ({ id: entry.id, title: entry.title, category: 'store' as const, source: entry.source, summary: entry.summary, updatedAt: entry.updated_at, kind: entry.kind, status: 'ready' as const, enabled: true, keywords: entry.keywords, itemCount: entry.item_count })),
    ...entries.map(entry => ({ id: entry.id, title: entry.title, category: entry.category, source: `${entry.source_type === 'table' ? '表格' : '文档'} · ${entry.format}`, summary: `${formatSize(entry.size_bytes)} · ${entry.name}`, updatedAt: entry.uploaded_at, kind: 'uploaded' as const, status: entry.status, enabled: entry.enabled, itemCount: entry.rows, document: entry })),
  ]
  const visible = knowledgeEntries.filter(entry => (tab === 'store' ? entry.category === 'store' : tab === 'platform' ? entry.category === 'platform' : true) && `${entry.title} ${entry.source} ${entry.summary}`.toLowerCase().includes(normalized))
  const activeKnowledge = connected.length + entries.filter(entry => entry.enabled).length
  const issueCards = [
    { label: '知识缺口', value: activeKnowledge ? 0 : 1, text: activeKnowledge ? '商城与文件知识均可检索' : '请同步商城或上传文件', tone: activeKnowledge ? 'good' : 'attention' },
    { label: '解析异常', value: entries.filter(entry => entry.status === 'needs_attention').length, text: '文件需要重新整理或上传', tone: '' },
    { label: '知识冲突', value: 0, text: '暂未发现重复冲突内容', tone: 'good' },
    { label: '合规风险', value: 0, text: '未发现敏感或越权内容', tone: 'good' },
  ]
  const category: KnowledgeCategory = tab === 'platform' ? 'platform' : 'store'
  const uploadFiles = async (files: File[]) => {
    if (!files.length) return
    setError('')
    const uploaded: KnowledgeDocument[] = []
    try {
      for (let index = 0; index < files.length; index += 1) {
        setUploading(`正在导入 ${index + 1}/${files.length}：${files[index].name}`)
        uploaded.push(await uploadKnowledgeDocument(files[index], category))
      }
      setEntries(current => [...uploaded.reverse(), ...current])
      setTab(category)
      notify(`已导入 ${uploaded.length} 个知识文件，Agent 可使用启用的内容回答问题`)
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : '知识文件上传失败。'
      setError(message)
      notify(message)
    } finally {
      setUploading('')
      if (fileInput.current) fileInput.current.value = ''
    }
  }
  const toggleEntry = async (entry: KnowledgeDocument) => {
    const enabled = !entry.enabled
    setEntries(current => current.map(item => item.id === entry.id ? { ...item, enabled } : item))
    try {
      const saved = await setKnowledgeDocumentEnabled(entry.id, enabled)
      setEntries(current => current.map(item => item.id === entry.id ? saved : item))
      notify(enabled ? '已启用该知识文件' : '已停用该知识文件')
    } catch (reason) {
      setEntries(current => current.map(item => item.id === entry.id ? entry : item))
      notify(reason instanceof Error ? reason.message : '知识文件状态保存失败。')
    }
  }
  return <>
    <PageTitle title="知识库" subtitle="同步 CHUNG YIP 商城商品与客服规则，也可上传补充文档和表格。"><Button primary icon="file" disabled={Boolean(uploading)} onClick={() => fileInput.current?.click()}>{uploading || '上传文件'}</Button><input ref={fileInput} className="nc-visually-hidden" type="file" multiple accept=".docx,.xlsx,.csv,.tsv,.md,.txt" onChange={event => void uploadFiles(Array.from(event.target.files || []))} /></PageTitle>
    <ModuleStats items={[
      { label: '知识健康度', value: activeKnowledge ? '100 分' : '待完善', hint: activeKnowledge ? '商城知识同步正常' : '等待知识来源', icon: 'shield' },
      { label: '商城同步', value: connected.length, hint: '客服规则、分类与商品资料', icon: 'store' },
      { label: '上传文件', value: entries.length, hint: '补充文档与业务表格', icon: 'file' },
      { label: '待处理问题', value: issueCards.reduce((total, issue) => total + issue.value, 0), hint: '建议优先补齐缺口与冲突', icon: 'bell', tone: 'attention' },
    ]} />
    <div className="nc-knowledge-layout">
      <section className="nc-panel nc-knowledge-main">
        <div className="nc-knowledge-head"><Tabs items={[{ id: 'operations', label: '知识运营' }, { id: 'store', label: '店铺知识' }, { id: 'platform', label: '平台知识' }]} value={tab} onChange={setTab} /><span>{visible.length} 条内容</span></div>
        {tab === 'operations' ? <>
          <button className="nc-knowledge-upload-zone" disabled={Boolean(uploading)} onClick={() => fileInput.current?.click()}><span><Icon name="file" size={22} /></span><strong>{uploading || '选择文档或表格'}</strong><small>支持 DOCX、XLSX、CSV、TSV、Markdown、TXT；单个文件不超过 8 MB</small></button>
          {error && <div className="nc-knowledge-upload-error">{error}</div>}
          <div className="nc-knowledge-issues">{issueCards.map(issue => <button key={issue.label} className={issue.tone} onClick={() => notify(`${issue.label}：${issue.text}`)}><span>{issue.label}<Icon name="chevron" size={12} /></span><strong>{issue.value}</strong><small>{issue.text}</small></button>)}</div>
          <div className="nc-knowledge-progress"><div className="nc-panel-heading"><h2>知识同步</h2><span className="nc-muted">商城知识与上传文件</span></div>{loading ? <Empty title="正在读取知识库" text="正在从后端加载商城与文件知识。" /> : !knowledgeEntries.length ? <Empty title="还没有可用知识" text="请检查商城连接，或上传业务文档和表格。" /> : knowledgeEntries.slice(0, 5).map(entry => <div className="nc-learning-row" key={entry.id}><span className={`nc-learning-icon ${entry.status}`}><Icon name={entry.status === 'ready' ? 'check' : 'refresh'} size={15} /></span><button className="nc-knowledge-entry-link" onClick={() => setSelectedEntry(entry)}><strong>{entry.title}</strong><small>{entry.source} · {entry.summary} · {formatTime(entry.updatedAt)}</small></button><div className="nc-learning-meter"><i style={{ width: entry.status === 'ready' ? '100%' : '40%' }} /></div><Badge tone={entry.status === 'ready' ? 'gray' : 'orange'}>{entry.kind === 'uploaded' ? '已入库' : '商城同步'}</Badge></div>)}</div>
        </> : <div className="nc-knowledge-list">{loading ? <Empty title="正在读取知识库" text="正在从后端加载商城与文件知识。" /> : !visible.length ? <Empty title="没有匹配的知识" text="可以调整搜索词，或上传文档和表格。" /> : visible.map(entry => <div className="nc-knowledge-row" key={entry.id}><span className="nc-knowledge-type"><Icon name={entry.category === 'platform' ? 'globe' : entry.kind === 'faq' ? 'chat' : entry.kind === 'uploaded' ? 'file' : 'store'} size={17} /></span><button className="nc-knowledge-entry-link" onClick={() => setSelectedEntry(entry)}><strong>{entry.title}</strong><small>{entry.source} · {entry.summary} · 更新于 {formatTime(entry.updatedAt)}</small></button><Badge tone={entry.status === 'ready' ? 'gray' : 'orange'}>{entry.kind === 'uploaded' ? entry.status === 'ready' ? '已入库' : '需处理' : entry.kind === 'faq' ? '客服规则' : entry.kind === 'category' ? '商品分类' : '商品资料'}</Badge><div className="nc-knowledge-row-actions"><button className="nc-knowledge-view" aria-label={`查看${entry.title}`} onClick={() => setSelectedEntry(entry)}>查看</button>{entry.document ? <Toggle value={entry.enabled} label={`${entry.title}启用状态`} onChange={() => void toggleEntry(entry.document!)} /> : <span className="nc-knowledge-synced" title="由 CHUNG YIP 商城自动同步"><Icon name="check" size={14} /></span>}</div></div>)}</div>}
      </section>
      <aside className="nc-panel nc-knowledge-side"><div className="nc-panel-heading"><h2>知识来源</h2><Icon name="link" size={16} /></div><div className="nc-source-card"><Icon name="store" /><span><strong>CHUNG YIP 商城</strong><small>商品目录与客服规则实时同步</small></span><b>{connected.length}</b></div><div className="nc-source-card"><Icon name="file" /><span><strong>业务文档</strong><small>DOCX、Markdown 与 TXT</small></span><b>{entries.filter(entry => entry.source_type === 'document').length}</b></div><div className="nc-source-card"><Icon name="trend" /><span><strong>业务表格</strong><small>XLSX、CSV 与 TSV</small></span><b>{entries.filter(entry => entry.source_type === 'table').length}</b></div><div className="nc-knowledge-note"><Icon name="shield" size={16} /><p><strong>数据说明</strong>商城知识只读并自动更新；启用的上传文件会作为补充知识参与 Agent 检索。</p></div></aside>
    </div>
    {selectedEntry && <KnowledgeViewer entry={selectedEntry} close={() => setSelectedEntry(null)} />}
  </>
}

function KnowledgeViewer({ entry, close }: { entry: KnowledgeViewEntry; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const [preview, setPreview] = useState(entry.document ? '' : entry.summary)
  const [previewTruncated, setPreviewTruncated] = useState(false)
  const [loading, setLoading] = useState(Boolean(entry.document))
  const [error, setError] = useState('')
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close() }, [])
  useEffect(() => {
    if (!entry.document) return
    let active = true
    void getKnowledgeDocument(entry.document.id).then(detail => {
      if (active) { setPreview(detail.preview); setPreviewTruncated(detail.preview_truncated) }
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : '无法读取知识内容。')
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [entry.document])
  const kindLabel = entry.kind === 'uploaded' ? entry.document?.source_type === 'table' ? '上传表格' : '上传文档' : entry.kind === 'faq' ? '客服规则' : entry.kind === 'category' ? '商品分类' : '商品资料'
  const statusLabel = entry.document ? entry.enabled ? '已启用' : '已停用' : '商城同步'
  const updatedAt = new Date(entry.updatedAt).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' })
  return <dialog className="nc-dialog nc-knowledge-viewer" ref={ref} aria-labelledby="nc-knowledge-viewer-title" onCancel={close} onClick={event => { if (event.target === ref.current) close() }}><div className="nc-dialog-inner"><button className="nc-icon-btn nc-dialog-close" aria-label="关闭知识详情" onClick={close}><Icon name="close" /></button><div className="nc-knowledge-viewer-heading"><span><Icon name={entry.kind === 'uploaded' ? 'file' : entry.kind === 'faq' ? 'chat' : 'store'} size={22} /></span><div><small>{kindLabel}</small><h2 id="nc-knowledge-viewer-title">{entry.title}</h2><p>{entry.source}</p></div></div><div className="nc-knowledge-viewer-meta"><div><span>状态</span><strong>{statusLabel}</strong></div><div><span>更新时间</span><strong>{updatedAt}</strong></div>{entry.itemCount !== null && entry.itemCount !== undefined && <div><span>{entry.kind === 'category' ? '商品数量' : '数据行数'}</span><strong>{entry.itemCount}</strong></div>}{entry.document && <div><span>文件格式</span><strong>{entry.document.format} · {entry.document.extracted_chars.toLocaleString()} 字符</strong></div>}</div>{entry.keywords?.length ? <div className="nc-knowledge-keywords"><span>关键词</span><div>{entry.keywords.map(keyword => <i key={keyword}>{keyword}</i>)}</div></div> : null}<section className="nc-knowledge-preview"><h3>{entry.document ? '解析内容预览' : '知识内容'}</h3>{loading ? <p className="nc-muted">正在读取知识内容…</p> : error ? <p className="nc-error">{error}</p> : <pre>{preview || '暂无可显示的内容。'}</pre>}{previewTruncated && <small>内容较长，这里展示前 20,000 个字符；Agent 检索仍使用完整解析文本。</small>}</section><div className="nc-knowledge-viewer-actions"><Button onClick={close}>关闭</Button></div></div></dialog>
}

function Inbox() {
  const { data, update, notify, scope, query, open, messageId, sendMailboxReply } = useConsole()
  const [channel, setChannel] = useState<'all' | 'chat' | 'email'>('all')
  const [status, setStatus] = useState('open')
  const [selected, setSelected] = useState(messageId)
  const [sideTab, setSideTab] = useState('customer')
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [sending, setSending] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [savingHandoff, setSavingHandoff] = useState(false)
  const items = data.messages.filter(m => storeMatch(m.storeId, scope) && (channel === 'all' || m.channel === channel) && (status === 'all' || m.status === status) && `${m.name} ${m.subject} ${m.preview} ${m.messages.map(a => a.text).join(' ')}`.toLowerCase().includes(query.toLowerCase()))
  const current = items.find(m => m.id === selected) || items[0]
  const store = data.stores.find(s => s.id === current?.storeId)
  const draft = current ? drafts[current.id] || '' : ''
  const setDraft = (text: string) => { if (current) setDrafts(value => ({ ...value, [current.id]: text })) }
  const select = (m: Message) => { setSelected(m.id); update(d => ({ ...d, messages: d.messages.map(a => a.id === m.id ? { ...a, unread: false } : a) })) }
  const send = async () => {
    if (!current || !draft.trim() || sending) return
    const reply = draft.trim()
    if (current.channel === 'email') {
      setSending(true)
      try {
        await sendMailboxReply(current, reply)
        setDraft('')
        update(d => ({ ...d, messages: d.messages.map(m => m.id === current.id ? { ...m, unread: false } : m) }))
        notify('邮件已通过 QQ 邮箱发送，回复内容未写入演示数据')
      } catch (caught) {
        notify(caught instanceof Error ? caught.message : '邮件回复发送失败，请稍后重试。')
      } finally {
        setSending(false)
      }
      return
    }
    if (current.id.startsWith('storefront-')) {
      setSending(true)
      try {
        const updated = await sendStorefrontConversationReply(current.id, reply)
        const message = sharedStorefrontConversation(updated)
        setDraft('')
        update(d => ({ ...d, messages: d.messages.map(item => item.id === current.id ? { ...message, unread: false } : item) }))
        notify('人工回复已写入商城会话，客户窗口将在几秒内收到')
      } catch (caught) {
        notify(caught instanceof Error ? caught.message : '人工回复发送失败，请稍后重试。')
      } finally {
        setSending(false)
      }
      return
    }
    update(d => ({ ...d, messages: d.messages.map(m => m.id === current.id ? { ...m, unread: false, preview: reply, messages: [...m.messages, { role: 'agent', text: reply, time: now() }] } : m) }))
    setDraft('')
    notify('在线会话回复已记录到工作台')
  }
  const generate = async () => {
    if (!current || generating) return
    const customerMessage = [...current.messages].reverse().find(message => message.role === 'customer')?.text || current.preview
    setGenerating(true)
    try {
      const result = await generateAgentDraft({ channel: current.channel, customer_name: current.name, subject: current.subject, message: customerMessage })
      setDraft(result.answer)
      notify(result.handoff_recommended ? '后端 Agent 已生成草稿，并建议转人工复核' : '后端 Agent 已生成回复建议，请核对后发送')
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : '后端 Agent 暂时无法生成回复建议。')
    } finally {
      setGenerating(false)
    }
  }
  const saveHandoff = async (next: 'pending' | 'claimed' | 'resolved') => {
    if (!current || !current.id.startsWith('storefront-') || savingHandoff) return
    setSavingHandoff(true)
    try {
      const updated = await updateStorefrontHandoff(current.id, next, next === 'claimed' ? 'NOVA 客服' : undefined)
      const message = sharedStorefrontConversation(updated)
      update(d => ({ ...d, messages: d.messages.map(item => item.id === current.id ? { ...message, unread: false } : item) }))
      notify(next === 'claimed' ? '已接管会话，客户窗口会显示人工客服已接入' : next === 'resolved' ? '人工会话已标记为解决' : '会话已重新进入人工队列')
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : '人工接管状态保存失败，请稍后重试。')
    } finally {
      setSavingHandoff(false)
    }
  }
  const toggleResolved = () => {
    if (!current) return
    if (current.id.startsWith('storefront-')) {
      void saveHandoff(current.status === 'resolved' ? 'pending' : 'resolved')
      return
    }
    update(d => ({ ...d, messages: d.messages.map(m => m.id === current.id ? { ...m, unread: false, status: m.status === 'open' ? 'resolved' : 'open' } : m) }))
    notify(current.status === 'open' ? '会话已标记为已解决' : '会话已重新打开')
  }
  return <>
    <PageTitle title="会话" subtitle="集中处理在线咨询与客户邮件，所有回复建议均需人工确认。"><Button icon="mail" onClick={() => open({ type: 'mail' })}>接入邮箱</Button></PageTitle>
    <div className="nc-inbox nc-panel">
      <div className="nc-inbox-toolbar"><Tabs className="nc-channel-tabs" label="会话渠道" items={[{ id: 'all', label: '全部消息' }, { id: 'chat', label: '在线会话' }, { id: 'email', label: '邮件' }]} value={channel} onChange={next => setChannel(next as 'all' | 'chat' | 'email')} /><select value={status} aria-label="会话状态" onChange={e => setStatus(e.target.value)}><option value="open">待处理</option><option value="resolved">已解决</option><option value="all">全部状态</option></select></div>
      <div className="nc-inbox-layout">
        <div className="nc-message-list"><div className="nc-list-caption">{items.length} 条会话<span>最近消息</span></div>{!items.length ? <Empty /> : items.map(m => <button className={`nc-message-item ${current?.id === m.id ? 'active' : ''}`} key={m.id} onClick={() => select(m)}><div className="nc-message-top"><Avatar text={m.initials} color={m.color} /><span><strong>{m.name}</strong><small><Icon name={m.channel === 'email' ? 'mail' : 'chat'} size={11} />{data.stores.find(s => s.id === m.storeId)?.name}</small></span><time>{m.time}</time></div><h3>{m.subject}</h3><p>{m.preview}</p><div className="nc-message-tags">{m.urgent ? <span className="nc-tag orange">优先处理</span> : <span className="nc-tag gray">一般咨询</span>}{m.unread && <i className="nc-unread-dot" />}</div></button>)}</div>
        <div className="nc-conversation">{!current ? <Empty title="当前没有待处理的会话" text="可以切换渠道或状态，查看其他客户消息。" /> : <><header className="nc-conversation-header"><Avatar text={current.initials} color={current.color} /><div><h3>{current.name}</h3><p>{current.channel === 'email' ? '邮件' : '在线会话'} · {store?.name}{current.assignedTo ? ` · ${current.assignedTo}接待` : ''}</p></div><div className="nc-conversation-actions">{current.id.startsWith('storefront-') && current.urgent && current.handoffStatus !== 'claimed' && <Button primary icon="chat" disabled={savingHandoff} onClick={() => void saveHandoff('claimed')}>{savingHandoff ? '接管中…' : '接管会话'}</Button>}<Button icon={current.status === 'resolved' ? 'refresh' : 'check'} disabled={savingHandoff} onClick={toggleResolved}>{current.status === 'resolved' ? '重新打开' : '标记解决'}</Button></div></header><div className="nc-conversation-body"><div className="nc-conversation-date">{current.channel === 'email' ? '真实邮箱会话' : '商城在线会话'}</div><div className="nc-thread-subject">{current.subject}</div>{current.messages.map((m, i) => <div className={`nc-bubble-wrap ${m.role}`} key={`${current.id}-${i}`}><span>{m.role === 'agent' ? 'NOVA 客服' : current.name}<time>{m.time}</time></span><div className="nc-bubble">{m.text}</div></div>)}{current.urgent && <div className="nc-ai-insight"><Icon name="shield" size={16} /><span><strong>{current.handoffStatus === 'claimed' ? '人工客服接待中' : '等待人工接管'}</strong> {current.handoffStatus === 'claimed' ? '后续回复会实际发送到客户商城窗口。' : '客户已请求人工协助，请接管后核实信息并回复。'}</span></div>}</div><div className="nc-composer"><div className="nc-composer-head"><span><Icon name={current.channel === 'email' ? 'mail' : 'chat'} size={14} />回复客户</span><button disabled={generating} onClick={() => void generate()}><Icon name="file" size={14} />{generating ? 'Agent 生成中…' : '生成回复建议'}</button></div><textarea aria-label="回复内容" placeholder="写下回复，或由后端 Agent 生成回复建议…" value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); void send() } }} /><div className="nc-composer-footer"><span>{current.channel === 'email' ? '通过 QQ 邮箱实际发送 · 不写入演示数据' : current.id.startsWith('storefront-') ? '发送到 CHUNG YIP 客户窗口 · ⌘ Enter 发送' : '记录到在线会话 · ⌘ Enter 发送'}</span><Button primary icon="send" disabled={!draft.trim() || sending} onClick={() => void send()}>{sending ? '发送中…' : '发送回复'}</Button></div></div></>}</div>
        {current && <ConversationBusinessPanel current={current} storeName={store?.name || '未关联店铺'} tab={sideTab} setTab={setSideTab} />}
      </div>
    </div>
  </>
}

function ConversationBusinessPanel({ current, storeName, tab, setTab }: { current: Message; storeName: string; tab: string; setTab: (value: string) => void }) {
  const { notify } = useConsole()
  const orderMatch = current.messages.map(message => message.text).join(' ').match(/(?:订单号|order(?:\s+number)?)[：:\s#]*([A-Z0-9_-]{4,80})/i)
  const orderNumber = orderMatch ? orderMatch[1] : ''
  const hasKnownOrder = Boolean(orderNumber)
  return <aside className="nc-business-panel">
    <div className="nc-business-tabs" role="tablist">{[{ id: 'customer', label: '客户' }, { id: 'order', label: '订单' }, { id: 'ticket', label: '工单' }, { id: 'ai', label: '模型记录' }].map(item => <button role="tab" aria-selected={tab === item.id} className={tab === item.id ? 'active' : ''} key={item.id} onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
    <div className="nc-business-content">
      {tab === 'customer' && <><div className="nc-customer-summary"><Avatar text={current.initials} color={current.color} /><span><strong>{current.name}</strong><small>{current.channel === 'email' ? '邮件客户' : '在线客户'} · {storeName}</small></span></div><div className="nc-business-section"><div className="nc-business-title"><strong>会话摘要</strong><Badge tone="gray">已更新</Badge></div><p>{current.urgent ? '客户正在咨询需要尽快确认的服务问题，表达了明确时间或售后诉求，建议先核实再承诺。' : '客户正在咨询商品或服务细节，当前情绪平稳，建议补充关键信息后给出准确答复。'}</p></div><div className="nc-business-section"><strong>客户标签</strong><div className="nc-customer-tags"><span>{current.urgent ? '优先跟进' : '普通咨询'}</span><span>{current.channel === 'email' ? '邮件渠道' : '在线咨询'}</span><button onClick={() => notify('标签编辑为本地演示入口')}>+ 添加</button></div></div><div className="nc-business-section"><strong>接待记录</strong><dl><div><dt>历史会话</dt><dd>{current.messages.length} 条消息</dd></div><div><dt>当前状态</dt><dd>{current.status === 'open' ? '待处理' : '已解决'}</dd></div><div><dt>最近联系</dt><dd>{current.time}</dd></div></dl></div></>}
      {tab === 'order' && <><div className="nc-business-empty-icon"><Icon name="store" size={18} /></div><div className="nc-business-section"><div className="nc-business-title"><strong>关联订单</strong><Badge tone={hasKnownOrder ? 'gray' : 'orange'}>{hasKnownOrder ? '已识别' : '待核实'}</Badge></div><h4>{orderNumber || '待客户补充'}</h4><p>{hasKnownOrder ? '已从客户会话中识别订单号；订单状态需由后端订单查询技能核验。' : '当前会话未识别到有效订单号，可请客户提供后再查询。'}</p></div><div className="nc-business-section"><strong>处理建议</strong><ul><li>核对订单号与收件信息</li><li>确认物流节点或售后状态</li><li>回复前避免承诺未核实结果</li></ul></div></>}
      {tab === 'ticket' && <><div className="nc-business-section"><div className="nc-business-title"><strong>人工接管</strong><Badge tone={current.handoffStatus === 'claimed' ? 'gray' : current.urgent ? 'orange' : 'gray'}>{current.handoffStatus === 'claimed' ? '接待中' : current.handoffStatus === 'pending' ? '待接管' : current.handoffStatus === 'resolved' ? '已解决' : '未触发'}</Badge></div><p>{current.handoffStatus === 'claimed' ? `${current.assignedTo || 'NOVA 客服'}已接管，会话回复将同步到客户商城窗口。` : current.handoffStatus === 'pending' ? '客户已进入人工队列，请在会话顶部接管后回复。' : current.handoffStatus === 'resolved' ? '本次人工跟进已经结束，可在会话顶部重新打开。' : '当前会话尚未触发人工接管。'}</p></div><div className="nc-business-section"><strong>流转信息</strong><dl><div><dt>责任团队</dt><dd>{current.urgent ? '售后支持' : '一线客服'}</dd></div><div><dt>接待人员</dt><dd>{current.assignedTo || '待分配'}</dd></div><div><dt>优先级</dt><dd>{current.urgent ? '高' : '普通'}</dd></div></dl></div></>}
      {tab === 'ai' && <><div className="nc-ai-log"><span><Icon name="spark" size={14} /></span><div><strong>识别会话意图</strong><p>{current.subject}</p><small>{current.time}</small></div></div><div className="nc-ai-log"><span><Icon name="file" size={14} /></span><div><strong>后端 Agent</strong><p>点击“生成回复建议”时调用后端技能与模型，不使用前端模板。</p><small>{current.time}</small></div></div><div className="nc-ai-log"><span><Icon name="shield" size={14} /></span><div><strong>回复风险检查</strong><p>{current.urgent ? '提示：不得承诺未确认的物流或退款结果' : '未发现高风险承诺'}</p><small>{current.time}</small></div></div></>}
    </div>
  </aside>
}

function Reviews() {
  const { data, scope, query } = useConsole()
  const [filter, setFilter] = useState('pending')
  const [selected, setSelected] = useState('r1')
  const [rating, setRating] = useState('all')
  const scoped = data.reviews.filter(r => storeMatch(r.storeId, scope))
  const items = scoped.filter(r => (filter === 'all' || (filter === 'pending' ? !r.reply : !!r.reply)) && (rating === 'all' || r.rating <= 3) && `${r.name} ${r.product} ${r.text}`.toLowerCase().includes(query.toLowerCase()))
  const current = items.find(r => r.id === selected) || items[0]
  return <><PageTitle title="评价管理" subtitle="统一查看客户评价，识别风险反馈并完成公开回复。" /><div className="nc-review-stats"><div><Icon name="star" /><span>样例平均评分</span><strong>{scoped.length ? (scoped.reduce((n, r) => n + r.rating, 0) / scoped.length).toFixed(1) : '—'}<small>/ 5</small></strong></div><div><Icon name="chat" /><span>待回复</span><strong>{scoped.filter(r => !r.reply).length}<small>条</small></strong></div><div><Icon name="shield" /><span>需要关注</span><strong>{scoped.filter(r => r.rating <= 3 && !r.reply).length}<small>条</small></strong></div></div><div className="nc-toolbar"><Tabs items={[{ id: 'pending', label: '待回复', count: scoped.filter(r => !r.reply).length }, { id: 'replied', label: '已回复' }, { id: 'all', label: '全部评论' }]} value={filter} onChange={setFilter} /><label className="nc-filter-select"><Icon name="filter" size={15} /><select aria-label="评论评分筛选" value={rating} onChange={e => setRating(e.target.value)}><option value="all">全部评分</option><option value="attention">3 星及以下</option></select></label></div><div className="nc-review-layout"><div className="nc-review-list">{!items.length ? <div className="nc-panel"><Empty /></div> : items.map(r => <button key={r.id} className={`nc-review-card ${current?.id === r.id ? 'selected' : ''}`} onClick={() => setSelected(r.id)}><div className="nc-review-head"><Avatar text={r.initials} color={r.color} /><span><strong>{r.name}</strong><small>{data.stores.find(s => s.id === r.storeId)?.name}</small></span><time>{r.date}</time></div><div className="nc-rating"><span aria-label={`${r.rating} 星`}>{'★'.repeat(r.rating)}<i>{'★'.repeat(5 - r.rating)}</i></span><span className={`nc-tag ${r.reply ? 'green' : r.rating <= 3 ? 'orange' : 'gray'}`}>{r.reply ? '已回复' : r.rating <= 3 ? '需要关怀' : '待回复'}</span></div><p>{r.text}</p><div className="nc-review-product"><Icon name="store" size={13} />{r.product}<Icon name="chevron" size={13} /></div></button>)}</div>{current && <ReviewEditor key={current.id} review={current} />}</div></>
}
function ReviewEditor({ review }: { review: Review }) {
  const { update, notify, data } = useConsole()
  const draft = data.reviewDrafts?.[review.id] ?? review.reply ?? ''
  const setDraft = (text: string) => update(d => ({ ...d, reviewDrafts: { ...d.reviewDrafts, [review.id]: text } }))
  const [generating, setGenerating] = useState(false)
  const generate = async () => {
    if (generating) return
    setGenerating(true)
    try {
      const result = await generateAgentDraft({ channel: 'review', customer_name: review.name, subject: review.product, message: `${review.rating} 星评价：${review.text}` })
      setDraft(result.answer)
      notify(result.handoff_recommended ? '后端 Agent 建议人工复核这条评价' : '后端 Agent 已生成评价回复建议')
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : '后端 Agent 暂时无法生成评价回复。')
    } finally {
      setGenerating(false)
    }
  }
  return <aside className="nc-panel nc-review-editor"><div className="nc-panel-heading"><h2>回复这条评论</h2><Icon name="chat" size={18} /></div><div className="nc-reply-context"><strong>{review.product}</strong><span>{review.rating <= 3 ? '建议先确认问题，再提供处理方式。' : '感谢客户反馈，回应具体建议。'}</span></div>{review.reply ? <div className="nc-published"><Badge>已回复 · 演示</Badge><p>{review.reply}</p><small>回复仅保存在当前浏览器。</small></div> : <><Button icon="file" className="nc-ai-generate" disabled={generating} onClick={() => void generate()}>{generating ? 'Agent 生成中…' : '生成回复建议'}</Button><label className="nc-field-label">回复内容<textarea aria-label="评论回复内容" value={draft} onChange={e => setDraft(e.target.value)} placeholder="认真回应客户的每一条反馈…" /></label><div className="nc-reply-note"><Icon name="shield" size={15} />公开回复中请勿包含客户订单号、联系方式等个人信息。</div><Button primary icon="send" className="nc-full-width" disabled={!draft.trim()} onClick={() => { update(d => ({ ...d, reviews: d.reviews.map(r => r.id === review.id ? { ...r, reply: draft.trim() } : r) })); notify('回复已保存到演示评论，未发布到平台') }}>发布回复（演示）</Button></>}</aside>
}

function Assistant() {
  const { data, notify } = useConsole()
  const [tab, setTab] = useState('agents')
  const [configuration, setConfiguration] = useState<AgentConfiguration | null>(null)
  const [error, setError] = useState('')
  const rows = [{ key: 'draft' as const, icon: 'file' as const, title: '回复建议', text: '在会话和评论中调用后端 Agent 生成草稿，由客服审核后发送。' }, { key: 'handoff' as const, icon: 'shield' as const, title: '复杂问题转人工', text: '退款争议、低置信度和情绪异常时由后端标记人工复核。' }, { key: 'translate' as const, icon: 'globe' as const, title: '多语言辅助', text: '后端识别客户语言并生成同语言回复建议。' }]
  useEffect(() => {
    let active = true
    getAgentConfiguration()
      .then(value => { if (active) { setConfiguration(value); setError('') } })
      .catch(caught => { if (active) setError(caught instanceof Error ? caught.message : '无法读取后端 Agent 配置。') })
    return () => { active = false }
  }, [])
  const saveSettings = async (values: Partial<Pick<AgentConfiguration, 'draft' | 'handoff' | 'translate' | 'tone' | 'cost_mode'>>) => {
    try {
      const saved = await updateAgentConfiguration(values)
      setConfiguration(saved)
      notify('Agent 配置已保存到后端')
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : 'Agent 配置保存失败。')
    }
  }
  const toggleSkill = async (skill: AgentSkill) => {
    try {
      const saved = await updateAgentSkill(skill.id, { enabled: !skill.enabled })
      setConfiguration(current => current ? { ...current, skills: current.skills.map(item => item.id === saved.id ? saved : item) } : current)
      notify(saved.enabled ? `${saved.title}已在后端启用` : `${saved.title}已在后端停用`)
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : 'Agent 技能保存失败。')
    }
  }
  const addSkill = async () => {
    try {
      const created = await createAgentSkill()
      setConfiguration(current => current ? { ...current, skills: [created, ...current.skills] } : current)
      setTab('skills')
      notify('自定义技能已在后端创建')
    } catch (caught) {
      notify(caught instanceof Error ? caught.message : 'Agent 技能创建失败。')
    }
  }
  if (error) return <><PageTitle title="Agent 管理" subtitle="读取和修改后端 Agent 运行配置。" /><section className="nc-panel"><Empty title="后端 Agent 配置暂不可用" text={error} /></section></>
  if (!configuration) return <><PageTitle title="Agent 管理" subtitle="读取和修改后端 Agent 运行配置。" /><section className="nc-panel"><Empty title="正在读取 Agent 配置" text="请稍候…" /></section></>
  const skills = configuration.skills
  const costLabels: Record<AgentCostMode, string> = { economy: '经济模式', balanced: '均衡模式', quality: '质量优先' }
  return <>
    <PageTitle title="Agent 管理" subtitle="管理后端接待策略、服务风格、成本模式和可调用技能。">{tab === 'skills' && <Button primary icon="plus" onClick={() => void addSkill()}>创建技能</Button>}</PageTitle>
    <div className="nc-toolbar nc-agent-toolbar"><Tabs items={[{ id: 'agents', label: 'Agent 管理' }, { id: 'skills', label: '技能管理', count: skills.length }]} value={tab} onChange={setTab} /><span className="nc-muted">配置保存在后端服务</span></div>
    <ModuleStats items={[{ label: '自动接待店铺', value: data.stores.filter(store => store.ai).length, hint: '已启用智能接待策略', icon: 'store' }, { label: '已启用技能', value: skills.filter(skill => skill.enabled).length, hint: `共 ${skills.length} 项后端技能`, icon: 'bolt' }, { label: '待处理会话', value: data.messages.filter(message => message.status === 'open').length, hint: '可调用后端生成回复建议', icon: 'chat' }, { label: '默认语气', value: configuration.tone, hint: '由后端生成策略控制', icon: 'globe' }]} />
    {tab === 'agents' ? <><section className="nc-panel nc-preferences"><h2>接待策略 <small>{rows.filter(row => configuration[row.key]).length}/{rows.length} 已启用</small></h2>{rows.map(r => <div className="nc-preference" key={r.key}><span className="nc-action-icon green"><Icon name={r.icon} /></span><div><h3>{r.title}</h3><p>{r.text}</p></div><Toggle value={configuration[r.key]} label={r.title} onChange={() => void saveSettings({ [r.key]: !configuration[r.key] })} /></div>)}<div className="nc-preference"><span className="nc-action-icon purple"><Icon name="chat" /></span><div><h3>服务风格</h3><p>后端生成会话与评价草稿时采用的默认表达风格。</p></div><select aria-label="默认品牌回复语气" value={configuration.tone} onChange={e => void saveSettings({ tone: e.target.value as AgentTone })}><option>亲切自然</option><option>简洁专业</option></select></div><div className="nc-preference"><span className="nc-action-icon purple"><Icon name="bolt" /></span><div><h3>成本控制</h3><p>后端生成策略使用的模型成本等级。</p></div><select aria-label="Agent 成本模式" value={configuration.cost_mode} onChange={e => void saveSettings({ cost_mode: e.target.value as AgentCostMode })}>{(Object.keys(costLabels) as AgentCostMode[]).map(mode => <option value={mode} key={mode}>{costLabels[mode]}</option>)}</select></div></section><div className="nc-info-strip"><Icon name="shield" size={19} /><span>回复建议、转人工标记、语言辅助和技能开关均由后端 API 执行并持久化。</span></div></> : <section className="nc-skill-grid">{skills.map(skill => <article className="nc-panel nc-skill-card" key={skill.id}><div className="nc-skill-card-head"><span><Icon name={skill.type === '官方技能' ? 'shield' : 'bolt'} size={18} /></span><Badge tone={skill.type === '官方技能' ? 'gray' : 'orange'}>{skill.type}</Badge><Toggle value={skill.enabled} label={`${skill.title}启用状态`} onChange={() => void toggleSkill(skill)} /></div><h2>{skill.title}</h2><p>{skill.text}</p><footer><span><Icon name="link" size={13} />{skill.tools} 个工具</span><span>后端技能</span></footer></article>)}</section>}
  </>
}

function ModalHost({ modal, close, reset }: { modal: Modal; close: () => void; reset: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { const d = ref.current; d?.showModal(); return () => d?.close() }, [])
  return <dialog className="nc-dialog" ref={ref} aria-labelledby="nc-modal-title" onCancel={close} onClick={e => { if (e.target === ref.current) { const r = ref.current.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) close() } }}><div className="nc-dialog-inner"><button className="nc-icon-btn nc-dialog-close" aria-label="关闭弹窗" onClick={close}><Icon name="close" /></button>{modal.type === 'store' ? <ConnectStore close={close} /> : modal.type === 'mail' ? <ConnectMailbox close={close} /> : modal.type === 'mail-sync' ? <StartMailboxSync id={modal.id} close={close} /> : modal.type === 'detail' ? <StoreDetail id={modal.id} close={close} /> : modal.type === 'settings' ? <><span className="nc-modal-icon"><Icon name="settings" size={27} /></span><h2 id="nc-modal-title">工作空间设置</h2><p className="nc-modal-description">NOVA AI 客服空间</p><div className="nc-details"><div><span>当前角色</span><strong>空间所有者</strong></div><div><span>数据存储</span><strong>后端服务 + 本机邮件缓存</strong></div><div><span>服务时区</span><strong>Asia/Shanghai</strong></div></div><p className="nc-note">重置只清理当前浏览器界面状态，不会覆盖后端 Agent 配置。</p><Button icon="refresh" onClick={() => { reset(); close() }}>重置前端状态</Button></> : <><span className="nc-modal-icon"><Icon name="help" size={27} /></span><h2 id="nc-modal-title">从一条客户消息开始</h2><p className="nc-modal-description">客服会话、邮箱同步和 Agent 配置均由后端服务提供。</p><ol className="nc-guide"><li><strong>连接你的渠道</strong><p>在店铺管理中查看线上商城，再接入服务邮箱并关联店铺。</p></li><li><strong>进入统一收件箱</strong><p>筛选在线会话或邮件，调用后端 Agent 生成草稿并人工确认。</p></li><li><strong>回复客户邮件</strong><p>邮件回复通过已接入的 QQ SMTP 发送，不保存为前端演示回复。</p></li></ol><div className="nc-note">QQ 邮箱授权码只保留在当前页面内存，刷新或关闭页面后需重新输入；Agent 开关、语气、成本模式和技能保存在后端。</div><Button primary onClick={close}>开始使用</Button></>}</div></dialog>
}

function ConnectStore({ close }: { close: () => void }) {
  const { data, update, notify } = useConsole()
  const [platform, setPlatform] = useState('Shopify')
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [error, setError] = useState('')
  const platforms = [{ name: 'Shopify', color: 'green', desc: '品牌独立站' }, { name: 'Lazada', color: 'purple', desc: '东南亚电商' }, { name: 'TikTok Shop', color: 'dark', desc: '内容电商' }, { name: '独立站', color: 'blue', desc: '自有商城' }]
  const submit = (e: FormEvent) => { e.preventDefault(); const clean = domain.trim().replace(/^https?:\/\//i, '').replace(/\/$/, ''); if (!name.trim() || !/^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}([/:?#][^\s]*)?$/i.test(clean)) { setError('请输入店铺名称和有效域名，例如 your-store.myshopify.com'); return } if (data.stores.some(s => s.domain.toLowerCase() === clean.toLowerCase())) { setError('该店铺地址已存在，请使用其他地址。'); return } update(d => ({ ...d, stores: [...d.stores, { id: uid(), name: name.trim(), domain: clean, url: `https://${clean}`, platform, color: platforms.find(p => p.name === platform)!.color, region: '全球 · 中文 / 英语', status: 'connected', ai: true, synced: '刚刚' }] })); notify('店铺已加入当前工作空间，尚未完成服务端授权'); close() }
  return <><span className="nc-modal-icon"><Icon name="store" size={27} /></span><span className="nc-step">第 {step} 步，共 2 步</span><h2 id="nc-modal-title">{step === 1 ? '连接一家新店铺' : `连接 ${platform} 店铺`}</h2><p className="nc-modal-description">{step === 1 ? '选择店铺所在的平台，开启统一的客户服务。' : '填写店铺信息，预览连接后的管理体验。'}</p>{step === 1 ? <><div className="nc-platform-options">{platforms.map(p => <button className={platform === p.name ? 'selected' : ''} key={p.name} onClick={() => setPlatform(p.name)}><Platform platform={p.name} color={p.color} /><strong>{p.name}</strong><small>{p.desc}</small>{platform === p.name && <Icon name="check" size={16} />}</button>)}</div><Button primary className="nc-full-width" onClick={() => setStep(2)}>继续 <Icon name="arrow" size={16} /></Button></> : <form onSubmit={submit}><label className="nc-field-label">店铺名称<input autoFocus required maxLength={50} placeholder="例如：NOVA 香港店" value={name} onChange={e => { setName(e.target.value); setError('') }} /></label><label className="nc-field-label">店铺域名<input required placeholder="your-store.myshopify.com" value={domain} onChange={e => { setDomain(e.target.value); setError('') }} /></label><div className="nc-note"><Icon name="shield" size={16} />此步骤模拟平台授权，不获取账号权限。真实接入将通过平台官方授权页面完成。</div>{error && <p className="nc-error" role="alert">{error}</p>}<div className="nc-modal-actions"><Button onClick={() => setStep(1)}>返回</Button><Button primary type="submit" icon="link">模拟授权并连接</Button></div></form>}</>
}

function ConnectMailbox({ close }: { close: () => void }) {
  const { data, update, notify, scope, startMailboxSync } = useConsole()
  const [provider, setProvider] = useState('QQ 邮箱')
  const [email, setEmail] = useState('')
  const [storeId, setStoreId] = useState(scope === 'all' ? data.stores[0]?.id || '' : scope)
  const [host, setHost] = useState('')
  const [port, setPort] = useState('993')
  const [authorizationCode, setAuthorizationCode] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  const isQQ = provider === 'QQ 邮箱'
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const normalizedEmail = email.trim().toLowerCase()
    if (!storeId) { setError('请先连接一家店铺。'); return }
    if (data.mailboxes.some(mailbox => mailbox.email.toLowerCase() === normalizedEmail)) { setError('这个邮箱已经接入，请勿重复添加。'); return }
    if (isQQ && !/^[a-z0-9._%+-]+@(qq|foxmail)\.com$/i.test(normalizedEmail)) { setError('请输入有效的 @qq.com 或 @foxmail.com 邮箱地址。'); return }
    if (isQQ && authorizationCode.trim().length < 8) { setError('请输入 QQ 邮箱生成的授权码，不要使用 QQ 登录密码。'); return }
    if (provider === 'IMAP / SMTP' && (!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(host.trim()) || !/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535)) { setError('请填写有效的 IMAP 服务器域名和 1–65535 范围内的端口。'); return }
    setError('')
    if (isQQ) {
      setConnecting(true)
      try {
        const result = await testQQMailbox(normalizedEmail, authorizationCode.trim())
        const mailboxId = uid()
        update(current => ({ ...current, mailboxes: [...current.mailboxes, { id: mailboxId, email: normalizedEmail, provider, storeId, enabled: true, connection: 'imap-verified', messages: result.messages, unread: result.unread, lastUid: result.last_uid }] }))
        startMailboxSync(mailboxId, normalizedEmail, storeId, authorizationCode.trim(), result.last_uid)
        notify(`QQ 邮箱已接入并开启自动同步：共 ${result.messages} 封，未读 ${result.unread} 封`)
        close()
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'QQ 邮箱连接验证失败，请稍后重试。')
      } finally {
        setConnecting(false)
      }
      return
    }
    update(current => ({ ...current, mailboxes: [...current.mailboxes, { id: uid(), email: normalizedEmail, provider, storeId, enabled: true, connection: 'demo' }] }))
    notify('邮箱已加入演示空间，未连接真实邮件服务器')
    close()
  }
  return <><span className="nc-modal-icon"><Icon name="mail" size={27} /></span><h2 id="nc-modal-title">接入服务邮箱</h2><p className="nc-modal-description">QQ 邮箱支持真实 IMAP 登录验证与当前页面内自动同步；其他服务商仍为演示接入。</p><form onSubmit={submit}><label className="nc-field-label">邮箱服务<select value={provider} onChange={event => { setProvider(event.target.value); setError(''); setAuthorizationCode('') }}><option>QQ 邮箱</option><option>Google Workspace</option><option>Microsoft 365</option><option>IMAP / SMTP</option></select></label><label className="nc-field-label">邮箱地址<input type="email" required placeholder={isQQ ? '你的QQ号@qq.com' : 'support@your-brand.com'} value={email} onChange={event => { setEmail(event.target.value); setError('') }} /></label>{isQQ && <label className="nc-field-label">QQ 邮箱授权码<input type="password" required autoComplete="off" maxLength={128} placeholder="不是 QQ 登录密码" value={authorizationCode} onChange={event => { setAuthorizationCode(event.target.value); setError('') }} /></label>}<label className="nc-field-label">关联店铺<select required value={storeId} onChange={event => setStoreId(event.target.value)}>{data.stores.map(store => <option key={store.id} value={store.id}>{store.name}</option>)}</select></label>{provider === 'IMAP / SMTP' && <div className="nc-form-grid"><label className="nc-field-label">IMAP 服务器<input required placeholder="imap.example.com" value={host} onChange={event => setHost(event.target.value)} /></label><label className="nc-field-label">SSL 端口<input required type="number" min="1" max="65535" value={port} onChange={event => setPort(event.target.value)} /></label></div>}<div className="nc-note"><Icon name="shield" size={16} />{isQQ ? '请先在 QQ 邮箱开启 IMAP/SMTP 并生成授权码。授权码只保留在当前页面内存中；系统每 60 秒读取新增邮件并加入客服会话，刷新或关闭页面后即失效。' : provider === 'IMAP / SMTP' ? '当前仅保存演示配置，不收集密码，也不会连接邮件服务器。' : '当前为模拟 OAuth 授权，不会读取或发送真实邮件。'}</div>{error && <p role="alert" className="nc-error">{error}</p>}<Button primary type="submit" className="nc-full-width" icon="link" disabled={connecting}>{isQQ ? connecting ? '正在验证 QQ 邮箱…' : '验证并开启自动同步' : provider === 'IMAP / SMTP' ? '保存演示配置' : '模拟授权并接入'}</Button></form></>
}

function StartMailboxSync({ id, close }: { id: string; close: () => void }) {
  const { data, update, notify, startMailboxSync } = useConsole()
  const mailbox = data.mailboxes.find(item => item.id === id)
  const [authorizationCode, setAuthorizationCode] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  if (!mailbox) return <><h2 id="nc-modal-title">邮箱不存在</h2><Button onClick={close}>关闭</Button></>
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (authorizationCode.trim().length < 8) { setError('请输入 QQ 邮箱生成的授权码，不要使用 QQ 登录密码。'); return }
    setConnecting(true)
    setError('')
    try {
      const result = await testQQMailbox(mailbox.email, authorizationCode.trim())
      update(current => ({ ...current, mailboxes: current.mailboxes.map(item => item.id === id ? { ...item, enabled: true, connection: 'imap-verified', messages: result.messages, unread: result.unread, lastUid: result.last_uid } : item) }))
      startMailboxSync(id, mailbox.email, mailbox.storeId, authorizationCode.trim(), result.last_uid)
      notify('QQ 邮箱自动同步已开启，将每 60 秒检查一次新增邮件')
      close()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'QQ 邮箱连接验证失败，请稍后重试。')
    } finally {
      setConnecting(false)
    }
  }
  return <><span className="nc-modal-icon"><Icon name="refresh" size={27} /></span><h2 id="nc-modal-title">启动 QQ 邮箱同步</h2><p className="nc-modal-description">{mailbox.email}</p><form onSubmit={submit}><label className="nc-field-label">QQ 邮箱授权码<input autoFocus type="password" required autoComplete="off" maxLength={128} placeholder="不是 QQ 登录密码" value={authorizationCode} onChange={event => { setAuthorizationCode(event.target.value); setError('') }} /></label><div className="nc-note"><Icon name="shield" size={16} />授权码仅保留在当前页面内存，不写入浏览器存储；刷新或关闭页面会自动停止同步。</div>{error && <p role="alert" className="nc-error">{error}</p>}<Button primary type="submit" className="nc-full-width" icon="refresh" disabled={connecting}>{connecting ? '正在验证并启动…' : '验证并启动同步'}</Button></form></>
}

function StoreDetail({ id, close }: { id: string; close: () => void }) {
  const { data, update, notify } = useConsole()
  const store = data.stores.find(s => s.id === id)!
  const [name, setName] = useState(store.name)
  const [region, setRegion] = useState(store.region)
  const save = (e: FormEvent) => { e.preventDefault(); if (!name.trim() || !region.trim()) return; update(d => ({ ...d, stores: d.stores.map(s => s.id === id ? { ...s, name: name.trim(), region: region.trim() } : s) })); notify('店铺信息已保存'); close() }
  const patch = (values: Partial<Store>) => update(d => ({ ...d, stores: d.stores.map(s => s.id === id ? { ...s, ...values } : s) }))
  return <><Platform platform={store.platform} color={store.color} /><h2 id="nc-modal-title">管理店铺</h2><p className="nc-modal-description">{store.domain}</p><form onSubmit={save}><label className="nc-field-label">店铺名称<input required maxLength={50} value={name} onChange={e => setName(e.target.value)} /></label><label className="nc-field-label">市场与服务语言<input required value={region} onChange={e => setRegion(e.target.value)} /></label><div className="nc-details"><div><span>连接状态</span><Badge tone={store.status === 'connected' ? 'green' : 'orange'}>{store.status === 'connected' ? '连接正常' : '授权已过期'}</Badge></div><div><span>最近同步</span><strong>{store.synced}</strong></div><div><span>关联邮箱</span><strong>{data.mailboxes.filter(m => m.storeId === id).length} 个</strong></div></div>{store.status === 'attention' ? <div className="nc-warning">店铺授权已过期。重新授权后可恢复消息同步与 AI 接待。</div> : null}<div className="nc-modal-actions"><a className="nc-btn" href={store.url} target="_blank" rel="noreferrer"><Icon name="link" size={16} />打开商城</a><Button icon="refresh" onClick={() => { patch({ status: 'connected', synced: '刚刚' }); notify(store.status === 'attention' ? '授权状态已恢复，请继续完成服务端密钥配置' : '连接状态已更新') }}>{store.status === 'attention' ? '恢复连接' : '更新状态'}</Button><Button primary type="submit">保存更改</Button></div></form></>
}
