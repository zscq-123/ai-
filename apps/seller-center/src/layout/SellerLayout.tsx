import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Merchant } from '../api'
import { iconPath } from '../shared/ui'

export type PageKey = 'overview' | 'products' | 'orders' | 'marketing' | 'design' | 'support' | 'settings'
const groups: Array<{ label: string; items: Array<{ key: PageKey; label: string; icon: string }> }> = [
  { label: '工作台', items: [{ key: 'overview', label: '店铺概览', icon: 'analytics' }] },
  { label: '商品与订单', items: [{ key: 'products', label: '我的商品', icon: 'package' }, { key: 'orders', label: '订单与发货', icon: 'delivery' }] },
  { label: '店铺经营', items: [{ key: 'marketing', label: '营销中心', icon: 'coupon' }, { key: 'design', label: '店铺装修', icon: 'store' }] },
  { label: '客户与设置', items: [{ key: 'support', label: '客服中心', icon: 'ai-support' }, { key: 'settings', label: '店铺设置', icon: 'account' }] },
]

export function SellerLayout({ page, merchant, editing, onNavigate, children }: {
  page: PageKey; merchant?: Merchant; editing: boolean; onNavigate: (page: PageKey) => boolean; children: ReactNode
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const sidebar = useRef<HTMLElement>(null)
  const toggle = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!menuOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const first = sidebar.current?.querySelector<HTMLButtonElement>('button')
    first?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setMenuOpen(false); toggle.current?.focus() }
      if (event.key !== 'Tab') return
      const buttons = [...sidebar.current?.querySelectorAll<HTMLButtonElement>('button') ?? []]
      const firstButton = buttons[0]
      const lastButton = buttons[buttons.length - 1]
      if (event.shiftKey && document.activeElement === firstButton) { event.preventDefault(); lastButton?.focus() }
      else if (!event.shiftKey && document.activeElement === lastButton) { event.preventDefault(); firstButton?.focus() }
    }
    document.addEventListener('keydown', keydown)
    return () => {
      document.body.style.overflow = previousOverflow; document.removeEventListener('keydown', keydown)
      if (sidebar.current?.contains(document.activeElement)) toggle.current?.focus()
    }
  }, [menuOpen])
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 801px)')
    const closeOnDesktop = () => { if (desktop.matches) setMenuOpen(false) }
    desktop.addEventListener('change', closeOnDesktop)
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [])
  const current = groups.flatMap((group) => group.items).find((item) => item.key === page)
  const navigate = (next: PageKey) => { if (onNavigate(next)) setMenuOpen(false) }
  return <div className={`seller-shell ${menuOpen ? 'menu-open' : ''}`}>
    <header className="topbar">
      <div className="topbar-start"><button ref={toggle} className="menu-toggle" type="button" aria-label={menuOpen ? '收起导航' : '展开导航'} aria-expanded={menuOpen} aria-controls="seller-sidebar" onClick={() => setMenuOpen((open) => !open)}><span /><span /><span /></button><button className="brand" onClick={() => navigate('overview')} aria-label="NOVA 商户中心首页"><img src="/brand/logo/nova-mark-image2.5-v1.png" alt="" /><b>NOVA</b><span>商户中心</span></button></div>
      <div className="top-links"><a href={`http://127.0.0.1:3001/${merchant ? `store/${merchant.id}` : ''}`} target="_blank" rel="noreferrer">查看店铺 <span aria-hidden="true">↗</span></a><button className="seller-user" onClick={() => navigate('settings')}><span className="account-avatar">{merchant?.storeName.slice(0, 1) ?? '店'}</span><span>{merchant?.storeName ?? '商户账号'}</span><span aria-hidden="true">⌄</span></button></div>
    </header>
    {menuOpen && <button className="navigation-scrim" aria-label="关闭导航" onClick={() => setMenuOpen(false)} />}
    <aside className="sidebar" id="seller-sidebar" ref={sidebar}>
      <div className="store-switcher"><img src={iconPath('store')} alt="" /><div><small>当前店铺</small><strong>{merchant?.storeName ?? '等待身份认证'}</strong></div></div>
      <nav aria-label="商户中心导航">{groups.map((group) => <div className="nav-group" key={group.label}><span className="nav-group-label">{group.label}</span>{group.items.map((item) => <button className={page === item.key ? 'active' : ''} aria-current={page === item.key ? 'page' : undefined} key={item.key} onClick={() => navigate(item.key)}><img src={iconPath(item.icon)} alt="" /><span>{item.label}</span></button>)}</div>)}</nav>
      <div className="sidebar-footer"><span>NOVA SELLER</span><p>每一笔生意，井然有序。</p></div>
    </aside>
    <main className="workspace" id="main-content"><nav className="breadcrumbs" aria-label="面包屑"><button onClick={() => navigate('overview')}>首页</button>{page !== 'overview' && <><span aria-hidden="true">›</span><button aria-current={!editing ? 'page' : undefined} onClick={() => navigate(page)}>{current?.label}</button></>}{editing && <><span aria-hidden="true">›</span><span aria-current="page">商品详情</span></>}</nav>{children}</main>
  </div>
}
