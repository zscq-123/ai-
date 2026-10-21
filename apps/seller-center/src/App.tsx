import { useEffect, useState } from 'react'
import { sellerApi, type SellerDashboard } from './api'
import { StoreDesigner } from './features/store-design/StoreDesigner'

type PageKey = 'overview' | 'products' | 'orders' | 'marketing' | 'design' | 'support' | 'settings'

const navigation: Array<{ key: PageKey; label: string; icon: string }> = [
  { key: 'overview', label: '店铺概览', icon: 'analytics' },
  { key: 'products', label: '商品管理', icon: 'package' },
  { key: 'orders', label: '订单与发货', icon: 'delivery' },
  { key: 'marketing', label: '营销中心', icon: 'coupon' },
  { key: 'design', label: '店铺装修', icon: 'store' },
  { key: 'support', label: 'AI 客服', icon: 'ai-support' },
  { key: 'settings', label: '店铺设置', icon: 'store' },
]

const money = (value: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value)
const statusText = (status: string) => ({ ACTIVE: '在售', DRAFT: '草稿', PAID: '待发货', FULFILLING: '备货中', SHIPPED: '已发货', COMPLETED: '已完成', RESOLVED: 'AI 已解决', HANDED_OFF: '已转人工' }[status] ?? status)
const iconPath = (name: string, size = 96) => `/brand/icons/image2.5/${size}/${name}-red.png`

export default function App() {
  const [page, setPage] = useState<PageKey>('overview')
  const [merchantId] = useState(() => sellerApi.currentMerchantId())
  const [dashboard, setDashboard] = useState<SellerDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!merchantId) { setLoading(false); return }
    let active = true
    setLoading(true); setError('')
    sellerApi.dashboard(merchantId).then((result) => { if (active) setDashboard(result) }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : '店铺数据加载失败') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [merchantId])

  const currentMerchant = dashboard?.merchant
  const retryDashboard = async () => {
    if (!merchantId) return
    setLoading(true)
    setError('')
    try { setDashboard(await sellerApi.dashboard(merchantId)) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '店铺数据加载失败') }
    finally { setLoading(false) }
  }

  return <div className="seller-shell">
    <header className="topbar">
      <div className="brand"><span>N</span><div><b>NOVA</b><small>商户中心</small></div></div>
      <div className="top-links"><a href="http://127.0.0.1:3001/">商城首页</a><button type="button" onClick={() => setPage('support')}>卖家帮助</button><button type="button" onClick={() => setPage('support')}>消息</button><div className="seller-user">{currentMerchant?.storeName ?? '商户账号'}⌄</div></div>
    </header>
    <aside className="sidebar">
      <div className="store-switcher"><img src={iconPath('store')} alt="" /><div><small>当前店铺</small><strong>{currentMerchant?.storeName ?? '等待身份认证'}</strong></div></div>
      <nav aria-label="商户中心导航">{navigation.map((item) => <button className={page === item.key ? 'active' : ''} key={item.key} onClick={() => setPage(item.key)}><img src={iconPath(item.icon)} alt="" /><span>{item.label}</span>{item.key === 'support' && <i>AI</i>}</button>)}</nav>
      <div className="sidebar-help"><b>需要帮助？</b><span>商户服务 7×24 小时在线</span><button onClick={() => setPage('support')}>联系智能客服</button></div>
    </aside>
    <main className="workspace">
      {error && <div className="error-banner" role="alert"><b>数据读取失败</b><span>{error}</span><button onClick={() => void retryDashboard()}>重试</button></div>}
      {loading ? <Loading /> : !merchantId ? <Empty title="请先登录商户账号" detail="系统会从受信任的登录身份读取当前店铺，不支持手动选择其他商户。" /> : !dashboard ? <Empty title="店铺数据暂不可用" detail="请检查商户接口或稍后重试。" /> : <SellerPage page={page} data={dashboard} onNavigate={setPage} />}
    </main>
  </div>
}

function SellerPage({ page, data, onNavigate }: { page: PageKey; data: SellerDashboard; onNavigate: (page: PageKey) => void }) {
  if (page === 'products') return <Products data={data} />
  if (page === 'orders') return <Orders data={data} />
  if (page === 'support') return <Support data={data} />
  if (page === 'design') return <StoreDesigner merchantId={data.merchant.id} products={data.products} />
  if (page === 'marketing') return <Empty title="营销中心" detail="当前店铺尚未创建优惠券或促销活动，系统不会展示模拟营销数据。" />
  if (page === 'settings') return <Settings data={data} />
  return <Overview data={data} onNavigate={onNavigate} />
}

function Overview({ data, onNavigate }: { data: SellerDashboard; onNavigate: (page: PageKey) => void }) {
  const cards = [
    ['今日实付金额', money(data.metrics.todayRevenue), 'wallet'],
    ['待处理订单', String(data.metrics.pendingFulfillment), 'delivery'],
    ['在售商品', String(data.metrics.activeProducts), 'package'],
    ['今日客服会话', String(data.support.conversationsToday), 'ai-support'],
  ]
  return <><PageTitle title={`你好，${data.merchant.storeName}`} detail={`数据更新于 ${new Date(data.generatedAt).toLocaleString('zh-CN')}`} /><section className="metric-grid">{cards.map(([label, value, icon]) => <article className="metric-card" key={label}><img src={iconPath(icon)} alt="" /><span>{label}</span><b>{value}</b><small>实时数据库</small></article>)}</section><section className="two-column"><div className="panel"><div className="panel-title"><h2>待办事项</h2><button onClick={() => onNavigate('orders')}>查看订单</button></div><div className="todo-grid"><button onClick={() => onNavigate('orders')}><b>{data.metrics.pendingFulfillment}</b><span>待履约</span></button><button onClick={() => onNavigate('products')}><b>{data.metrics.lowStockProducts}</b><span>低库存商品</span></button><button onClick={() => onNavigate('support')}><b>{data.support.handedOffToday}</b><span>待人工接待</span></button></div></div><div className="panel"><div className="panel-title"><h2>AI 客服表现</h2><button onClick={() => onNavigate('support')}>客服中心</button></div><Ring value={data.support.resolutionRate} /><div className="support-caption"><b>{data.support.resolutionRate.toFixed(1)}%</b><span>自主解决率</span></div></div></section><section className="panel"><div className="panel-title"><h2>最新订单</h2><button onClick={() => onNavigate('orders')}>全部订单</button></div><OrderTable data={data} /></section></>
}

function Products({ data }: { data: SellerDashboard }) { return <><PageTitle title="商品管理" detail="仅显示当前店铺的商品、价格与库存。" /><section className="panel"><Table headers={['商品', 'SKU', '售价', '库存', '状态', '更新时间']} rows={data.products.map((item) => [item.name, item.skuCode, money(item.salePrice), String(item.availableStock), statusText(item.status), new Date(item.updatedAt).toLocaleString('zh-CN')])} empty="当前店铺暂无商品" /></section></> }
function Orders({ data }: { data: SellerDashboard }) { return <><PageTitle title="订单与发货" detail="订单已按当前店铺隔离。" /><section className="panel"><OrderTable data={data} /></section></> }
function OrderTable({ data }: { data: SellerDashboard }) { return <Table headers={['订单号', '客户', '金额', '状态', '下单时间']} rows={data.recentOrders.map((item) => [item.orderNo, item.customerName, money(item.totalAmount), statusText(item.status), new Date(item.createdAt).toLocaleString('zh-CN')])} empty="当前店铺暂无订单" /> }

function Support({ data }: { data: SellerDashboard }) { return <><PageTitle title="AI 客服" detail="每个店铺拥有独立客服会话、知识与服务指标。" /><section className="support-summary"><article><span>今日会话</span><b>{data.support.conversationsToday}</b></article><article><span>AI 已解决</span><b>{data.support.resolvedToday}</b></article><article><span>转人工</span><b>{data.support.handedOffToday}</b></article><article><span>自主解决率</span><b>{data.support.resolutionRate.toFixed(1)}%</b></article></section><section className="panel"><div className="panel-title"><h2>最近会话</h2><span className="live-dot">实时记录</span></div><Table headers={['会话', '状态', '消息数', '最近意图', '开始时间']} rows={data.conversations.map((item) => [item.id.slice(0, 8), statusText(item.status), String(item.messageCount), item.lastIntent ?? '—', new Date(item.startedAt).toLocaleString('zh-CN')])} empty="当前店铺暂无客服会话" /></section></> }

function Settings({ data }: { data: SellerDashboard }) { return <><PageTitle title="店铺设置" detail="当前商户身份与客服绑定信息。" /><section className="panel settings-list"><label><span>店铺名称</span><input value={data.merchant.storeName} readOnly /></label><label><span>企业主体</span><input value={data.merchant.legalName} readOnly /></label><label><span>商户 ID</span><input value={data.merchant.id} readOnly /></label><div className="binding"><img src={iconPath('ai-support')} alt="" /><div><b>店铺 AI 客服已绑定</b><span>所有新会话自动关联当前商户 ID，其他店铺无法查看。</span></div></div></section></> }

function PageTitle({ title, detail }: { title: string; detail: string }) { return <div className="page-title"><div><h1>{title}</h1><p>{detail}</p></div><button>卖家帮助</button></div> }
function Loading() { return <div className="loading"><i /><span>正在读取店铺真实数据…</span></div> }
function Empty({ title, detail }: { title: string; detail: string }) { return <div className="empty"><img src={iconPath('store', 256)} alt="" /><h1>{title}</h1><p>{detail}</p></div> }
function Ring({ value }: { value: number }) { return <div className="ring" style={{ background: `conic-gradient(#ee4d2d ${Math.max(0, Math.min(100, value))}%, #f1f3f6 0)` }}><span /></div> }
function Table({ headers, rows, empty }: { headers: string[]; rows: string[][]; empty: string }) { return <div className="table-wrap"><table><thead><tr>{headers.map((item) => <th key={item}>{item}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${row[0]}-${index}`}>{row.map((cell, cellIndex) => <td key={`${cell}-${cellIndex}`}>{cell}</td>)}</tr>)}</tbody></table>{rows.length === 0 && <div className="table-empty">{empty}</div>}</div> }
