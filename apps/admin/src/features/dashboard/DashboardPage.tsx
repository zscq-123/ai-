import { Alert, Button, Card, Col, Empty, Progress, Row, Skeleton, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { CommerceIcon } from '../../shared/ui/CommerceIcon'
import { commerceApi, type OperationsDashboard, type OrderSummary } from '../../shared/api/commerceApi'
import styles from './dashboard.module.css'

const columns = [
  { title: '订单编号', dataIndex: 'orderNo' },
  { title: '企业客户', dataIndex: 'customerName' },
  { title: '订单金额', dataIndex: 'totalAmount', render: (value: number) => money(value) },
  { title: '状态', dataIndex: 'status', render: (status: string) => <Tag color={status === 'COMPLETED' ? 'success' : status === 'PAID' ? 'processing' : 'warning'}>{orderStatus(status)}</Tag> },
]

const money = (value: number) => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value)
const integer = (value: number) => new Intl.NumberFormat('zh-CN').format(value)
const orderStatus = (value: string) => ({ PENDING_PAYMENT: '待付款', PAID: '待履约', FULFILLING: '履约中', SHIPPED: '已发货', COMPLETED: '已完成', CANCELLED: '已取消', REFUND_PENDING: '退款中', REFUNDED: '已退款' }[value] ?? value)

export function DashboardPage({ onNavigate }: { onNavigate?: (key: string) => void }) {
  const [data, setData] = useState<OperationsDashboard | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = async () => { setLoading(true); setError(''); try { setData(await commerceApi.dashboard()) } catch (reason) { setError(reason instanceof Error ? reason.message : '经营数据加载失败') } finally { setLoading(false) } }
  useEffect(() => {
    let active = true
    commerceApi.dashboard()
      .then((result) => { if (active) setData(result) })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : '经营数据加载失败') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])
  const maxRevenue = useMemo(() => Math.max(1, ...(data?.revenueTrend.map((item) => Number(item.amount)) ?? [])), [data])
  if (loading && !data) return <Skeleton active paragraph={{ rows: 12 }} />
  if (!data) return <Alert type="error" showIcon message="无法读取真实经营数据" description={error} action={<Button onClick={() => void load()}>重试</Button>} />
  const revenueChange = data.metrics.yesterdayRevenue === 0 ? null : ((data.metrics.todayRevenue - data.metrics.yesterdayRevenue) / data.metrics.yesterdayRevenue) * 100
  const metrics = [
    { label: '今日实付交易额', value: money(data.metrics.todayRevenue), detail: revenueChange == null ? '昨日无实付订单' : `${revenueChange >= 0 ? '+' : ''}${revenueChange.toFixed(1)}% 较昨日`, icon: 'wallet' as const },
    { label: '待履约订单', value: integer(data.metrics.pendingFulfillment), detail: '来自订单数据库', icon: 'package' as const },
    { label: '今日新增客户', value: integer(data.metrics.newCustomers), detail: '来自客户数据库', icon: 'account' as const },
    { label: '在售商品', value: integer(data.metrics.activeProducts), detail: `${data.metrics.pendingMerchants} 家商户待审核`, icon: 'store' as const },
  ]
  return (
    <div className={styles.page}>
      <div className={styles.welcome}><div><Typography.Title level={2}>经营概览</Typography.Title><Typography.Text type="secondary">数据更新时间：{new Date(data.generatedAt).toLocaleString('zh-CN')}</Typography.Text></div><Button onClick={() => void load()} loading={loading}>刷新数据</Button></div>
      {error && <Alert className={styles.inlineAlert} type="warning" showIcon message={error} />}
      <Row gutter={[16, 16]}>{metrics.map((item) => <Col xs={24} sm={12} xl={6} key={item.label}><Card className={styles.metricCard}><div className={styles.metricIcon}><CommerceIcon name={item.icon} size={54} /></div><Typography.Text type="secondary">{item.label}</Typography.Text><strong>{item.value}</strong><span>{item.detail}</span></Card></Col>)}</Row>
      <Row gutter={[16, 16]} className={styles.lower}>
        <Col xs={24} xl={16}><Card title="实付交易趋势" extra={<Typography.Text type="secondary">最近 12 小时</Typography.Text>} className={styles.chartCard}>{data.revenueTrend.length ? <div className={styles.trendBars}>{data.revenueTrend.map((point) => <div className={styles.trendPoint} key={point.bucket} title={`${new Date(point.bucket).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} · ${money(point.amount)}`}><i style={{ height: `${Math.max(2, Number(point.amount) / maxRevenue * 100)}%` }} /><span>{new Date(point.bucket).getHours().toString().padStart(2, '0')}:00</span></div>)}</div> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="最近 12 小时暂无实付交易" />}</Card></Col>
        <Col xs={24} xl={8}><Card title="AI 客服质效" className={styles.aiCard}><div className={styles.aiTitle}><CommerceIcon name="aiSupport" size={68} /><div><strong>{integer(data.support.conversationsToday)}</strong><span>今日真实会话</span></div></div><Space orientation="vertical" size={20} style={{ width: '100%' }}><div><div className={styles.progressLabel}><span>自主解决率</span><b>{data.support.resolutionRate.toFixed(1)}%</b></div><Progress percent={data.support.resolutionRate} showInfo={false} /></div><div><div className={styles.progressLabel}><span>满意度</span><b>{data.support.satisfactionRate.toFixed(1)}%</b></div><Progress percent={data.support.satisfactionRate} showInfo={false} strokeColor="#12b76a" /></div></Space></Card></Col>
      </Row>
      <Card title="最新订单" extra={<Button type="link" onClick={() => onNavigate?.('orders')}>查看全部</Button>}><Table<OrderSummary> rowKey="id" columns={columns} dataSource={data.recentOrders} pagination={false} scroll={{ x: 640 }} locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="数据库中暂无订单" /> }} /></Card>
    </div>
  )
}
