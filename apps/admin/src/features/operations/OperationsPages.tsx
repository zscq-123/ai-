import { Alert, Button, Card, Empty, Image, Progress, Space, Statistic, Table, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import {
  commerceApi,
  productMediaUrl,
  productMoney,
  type CustomerSummary,
  type OrderSummary,
  type ProductSummary,
} from '../../shared/api/commerceApi'
import { SupportKnowledgePanel } from '../support/SupportKnowledgePanel'

const money = (value: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value)
const dateTime = (value: string | null) => value ? new Date(value).toLocaleString('zh-CN') : '—'
const statusLabel = (value: string) => ({ ACTIVE: '正常', DISABLED: '已停用', DRAFT: '草稿', PENDING_REVIEW: '待审核', REJECTED: '已驳回', ARCHIVED: '已归档', PENDING_PAYMENT: '待付款', PAID: '待履约', FULFILLING: '履约中', SHIPPED: '已发货', COMPLETED: '已完成', CANCELLED: '已取消', REFUND_PENDING: '退款中', REFUNDED: '已退款' }[value] ?? value)

function PageHeader({ title, description }: { title: string; description: string }) {
  return <div style={{ marginBottom: 24 }}><Typography.Title level={2} style={{ margin: 0 }}>{title}</Typography.Title><Typography.Text type="secondary">{description}</Typography.Text></div>
}

function useRemote<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => { setLoading(true); setError(''); try { setData(await loader()) } catch (reason) { setError(reason instanceof Error ? reason.message : '数据加载失败') } finally { setLoading(false) } }, [loader])
  useEffect(() => {
    let active = true
    loader()
      .then((result) => { if (active) setData(result) })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : '数据加载失败') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loader])
  return { data, error, loading, load }
}

function ErrorBanner({ error, reload }: { error: string; reload: () => void }) {
  return error ? <Alert style={{ marginBottom: 16 }} type="error" showIcon message="真实数据读取失败" description={error} action={<Button onClick={reload}>重试</Button>} /> : null
}

export function OrdersPage() {
  const state = useRemote(commerceApi.orders)
  return <div><PageHeader title="订单履约" description="订单金额、客户与履约状态均直接读取订单数据库。" /><ErrorBanner error={state.error} reload={() => void state.load()} /><Card><Table<OrderSummary> rowKey="id" loading={state.loading} dataSource={state.data ?? []} locale={{ emptyText: <Empty description="数据库中暂无订单" /> }} columns={[
    { title: '订单编号', dataIndex: 'orderNo' },
    { title: '客户', render: (_, row) => <div><b>{row.customerName}</b><br/><Typography.Text type="secondary">{row.customerEmail ?? row.customerId}</Typography.Text></div> },
    { title: '金额', dataIndex: 'totalAmount', render: money },
    { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={value === 'COMPLETED' ? 'success' : 'processing'}>{statusLabel(value)}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt', render: dateTime },
  ]} /></Card></div>
}

function ProductThumbnail({ src, name }: { src: string; name: string }) {
  const [failed, setFailed] = useState(false)
  if (failed) return <span role="status" aria-label={`${name}：源图片暂不可用`} style={{ display: 'grid', placeContent: 'center', width: 64, height: 64, flexShrink: 0, background: '#f5f5f7', color: '#666', fontSize: 12, textAlign: 'center', borderRadius: 6 }}>图片<br />暂不可用</span>
  return <Image width={64} height={64} style={{ objectFit: 'contain' }} src={src} alt={name} onError={() => setFailed(true)} />
}

export function ProductsPage({ onEdit }: { onEdit: () => void }) {
  const state = useRemote(commerceApi.products)
  return <div><PageHeader title="商品中心" description="商品、图片和原币种价格来自数据库。采集商品先保存为草稿，不代表已入驻、已授权或已上架。" /><ErrorBanner error={state.error} reload={() => void state.load()} /><Card extra={<Space><Button onClick={() => void state.load()} loading={state.loading}>刷新商品</Button><Button type="primary" onClick={onEdit} disabled={!state.data?.length}>编辑首个商品</Button></Space>}><Table<ProductSummary> rowKey="id" loading={state.loading} dataSource={state.data ?? []} scroll={{ x: 1100 }} pagination={{ defaultPageSize: 10, showTotal: (total) => `共 ${total} 件商品` }} locale={{ emptyText: <Empty description="数据库中暂无商品" /> }} columns={[
    { title: '商品', width: 360, render: (_, row) => <Space align="start">{row.coverImageUrl && <ProductThumbnail key={row.coverImageUrl} src={productMediaUrl(row.coverImageUrl)} name={row.name} />}<div style={{ overflowWrap: 'anywhere' }}><b>{row.name}</b><br/><Typography.Text type="secondary">{row.skuCode}</Typography.Text></div></Space> },
    { title: '店铺', dataIndex: 'merchantName', filters: [...new Set((state.data ?? []).map((item) => item.merchantName))].map((name) => ({ text: name, value: name })), onFilter: (value, row) => row.merchantName === value },
    { title: '类目', dataIndex: 'categoryName', render: (value: string | null) => value ?? '未分类' },
    { title: '售价', dataIndex: 'salePrice', render: (value: number, row) => <span style={{ whiteSpace: 'nowrap' }}>{productMoney(value, row.currency)}</span> },
    { title: '库存', dataIndex: 'availableStock' },
    { title: '状态', dataIndex: 'status', filters: [{ text: '草稿', value: 'DRAFT' }, { text: '在售', value: 'ACTIVE' }, { text: '待审核', value: 'PENDING_REVIEW' }], onFilter: (value, row) => row.status === value, render: (value: string) => <Tag color={value === 'ACTIVE' ? 'success' : 'default'}>{statusLabel(value)}</Tag> },
    { title: '更新时间', dataIndex: 'updatedAt', render: dateTime },
  ]} /></Card></div>
}

export function CustomersPage() {
  const state = useRemote(commerceApi.customers)
  return <div><PageHeader title="客户管理" description="账号、登录时间和成交数据来自客户与订单数据库。" /><ErrorBanner error={state.error} reload={() => void state.load()} /><Card><Table<CustomerSummary> rowKey="id" loading={state.loading} dataSource={state.data ?? []} locale={{ emptyText: <Empty description="数据库中暂无注册客户" /> }} columns={[
    { title: '客户', render: (_, row) => <div><b>{row.displayName}</b><br/><Typography.Text type="secondary">{row.email}</Typography.Text></div> },
    { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={value === 'ACTIVE' ? 'success' : 'default'}>{statusLabel(value)}</Tag> },
    { title: '订单数', dataIndex: 'orderCount' },
    { title: '累计实付', dataIndex: 'totalSpend', render: money },
    { title: '注册时间', dataIndex: 'createdAt', render: dateTime },
    { title: '最近登录', dataIndex: 'lastLoginAt', render: dateTime },
  ]} /></Card></div>
}

export function SupportPage() {
  const state = useRemote(commerceApi.dashboard)
  const support = state.data?.support
  return <div><PageHeader title="AI 客服" description="只统计实际写入客服会话库的数据；没有会话时显示 0。" /><ErrorBanner error={state.error} reload={() => void state.load()} /><Space orientation="vertical" size={16} style={{ width: '100%' }}>
    <Card loading={state.loading}><Space size={48} wrap><Statistic title="今日会话" value={support?.conversationsToday ?? 0} /><Statistic title="AI 自主解决" value={support?.resolvedToday ?? 0} /><Statistic title="转人工" value={support?.handedOffToday ?? 0} /></Space></Card>
    <Card title="服务质量" loading={state.loading}><Metric label="自主解决率" value={support?.resolutionRate ?? 0} /><Metric label="满意度" value={support?.satisfactionRate ?? 0} color="#12b76a" /></Card>
    <SupportKnowledgePanel />
  </Space></div>
}

function Metric({ label, value, color }: { label: string; value: number; color?: string }) {
  return <div style={{ marginBottom: 20 }}><div style={{ display: 'flex', justifyContent: 'space-between' }}><span>{label}</span><b>{value.toFixed(1)}%</b></div><Progress percent={value} showInfo={false} strokeColor={color} /></div>
}

export function MarketingPage() {
  return <div><PageHeader title="营销权益" description="当前数据库尚未建立营销活动，因此不展示模拟优惠券或虚构统计。" /><Card><Empty description="暂无已配置的营销活动" /></Card></div>
}
