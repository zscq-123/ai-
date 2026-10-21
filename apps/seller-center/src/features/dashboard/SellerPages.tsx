import type { SellerDashboard } from '../../api'
import type { PageKey } from '../../layout/SellerLayout'
import { Empty, iconPath, money, PageTitle, statusText, Table } from '../../shared/ui'

export function Overview({ data, onNavigate }: { data: SellerDashboard; onNavigate: (page: PageKey) => void }) {
  const cards = [
    ['今日实付金额', money(data.metrics.todayRevenue)],
    ['待处理订单', String(data.metrics.pendingFulfillment)],
    ['在售商品', String(data.metrics.activeProducts)],
    ['今日客服会话', String(data.support.conversationsToday)],
  ]
  return <><PageTitle title="店铺概览" detail={`${data.merchant.storeName} · 更新于 ${new Date(data.generatedAt).toLocaleString('zh-CN')}`} actions={<a className="secondary-button" href={`http://127.0.0.1:3001/store/${data.merchant.id}`} target="_blank" rel="noreferrer">查看店铺 ↗</a>} /><section className="metric-grid" aria-label="店铺经营概况">{cards.map(([label, value]) => <article className="metric-card" key={label}><span>{label}</span><b>{value}</b><small>{label === '今日实付金额' ? '已支付订单金额' : label === '待处理订单' ? '等待发货与履约' : label === '在售商品' ? '当前可购买商品' : '今日新建会话'}</small></article>)}</section><section className="two-column"><div className="panel"><div className="panel-title"><h2>待办事项</h2><button onClick={() => onNavigate('orders')}>查看订单 ›</button></div><div className="todo-grid"><button onClick={() => onNavigate('orders')}><b>{data.metrics.pendingFulfillment}</b><span>待履约</span></button><button onClick={() => onNavigate('products')}><b>{data.metrics.lowStockProducts}</b><span>低库存商品</span></button><button onClick={() => onNavigate('support')}><b>{data.support.handedOffToday}</b><span>转人工会话</span></button></div></div><div className="panel"><div className="panel-title"><h2>客服表现</h2><button onClick={() => onNavigate('support')}>客服中心 ›</button></div><div className="service-performance"><div className="ring" style={{ background: `conic-gradient(#007aff ${Math.max(0, Math.min(100, data.support.resolutionRate))}%, #eceef2 0)` }}><div><b>{data.support.resolutionRate.toFixed(1)}%</b><span>自主解决率</span></div></div><p>{data.support.conversationsToday === 0 ? '今日暂无会话' : `今日已解决 ${data.support.resolvedToday} 个会话`}</p></div></div></section><section className="panel"><div className="panel-title"><h2>最新订单</h2><button onClick={() => onNavigate('orders')}>全部订单 ›</button></div><OrderTable data={data} /></section></>
}

export function Orders({ data }: { data: SellerDashboard }) {
  return <><PageTitle title="订单与发货" detail="查看店铺订单与当前履约进度。" /><section className="panel"><div className="panel-title"><h2>店铺订单</h2><span className="muted">{data.recentOrders.length} 笔近期订单</span></div><OrderTable data={data} /></section></>
}

function OrderTable({ data }: { data: SellerDashboard }) {
  return <Table headers={['订单号', '客户', '金额', '状态', '下单时间']} rows={data.recentOrders.map((item) => [item.orderNo, item.customerName, money(item.totalAmount), statusText(item.status), new Date(item.createdAt).toLocaleString('zh-CN')])} empty="当前店铺暂无订单" />
}

export function Support({ data }: { data: SellerDashboard }) {
  return <><PageTitle title="客服中心" detail="查看本店客服会话、处理进度与服务表现。" /><section className="support-summary"><article><span>今日会话</span><b>{data.support.conversationsToday}</b></article><article><span>已解决</span><b>{data.support.resolvedToday}</b></article><article><span>转人工</span><b>{data.support.handedOffToday}</b></article><article><span>自主解决率</span><b>{data.support.resolutionRate.toFixed(1)}%</b></article></section><section className="panel"><div className="panel-title"><h2>最近会话</h2><span className="muted">仅显示本店会话</span></div><Table headers={['会话', '状态', '消息数', '最近意图', '开始时间']} rows={data.conversations.map((item) => [item.id.slice(0, 8), statusText(item.status), String(item.messageCount), item.lastIntent ?? '—', new Date(item.startedAt).toLocaleString('zh-CN')])} empty="当前店铺暂无客服会话" /></section></>
}

export function Marketing() {
  return <><PageTitle title="营销中心" detail="管理店铺的促销与优惠活动。" /><section className="panel"><Empty title="暂无营销活动" detail="优惠券与促销活动创建功能尚未开放。" /></section></>
}

export function Settings({ data }: { data: SellerDashboard }) {
  return <><PageTitle title="店铺设置" detail="查看店铺资料与客服关联信息。" /><section className="panel settings-list"><div className="panel-title"><h2>基本资料</h2><span className="muted">店铺资料当前为只读</span></div><label><span>店铺名称</span><input value={data.merchant.storeName} readOnly /></label><label><span>企业主体</span><input value={data.merchant.legalName} readOnly /></label><label><span>商户编号</span><input value={data.merchant.id} readOnly /></label><div className="binding"><img src={iconPath('ai-support')} alt="" /><div><b>专属客服已关联</b><span>本店买家会话将进入当前店铺的客服中心。</span></div></div></section></>
}
