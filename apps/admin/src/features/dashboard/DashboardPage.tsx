import { Button, Card, Col, Progress, Row, Space, Table, Tag, Typography } from 'antd'
import { CommerceIcon } from '../../shared/ui/CommerceIcon'
import { metrics, orders } from './dashboardData'
import styles from './dashboard.module.css'

const columns = [
  { title: '订单编号', dataIndex: 'id' },
  { title: '企业客户', dataIndex: 'customer' },
  { title: '订单金额', dataIndex: 'amount' },
  { title: '状态', dataIndex: 'status', render: (status: string) => <Tag color={status === '已完成' ? 'success' : status === '审批中' ? 'processing' : 'warning'}>{status}</Tag> },
]

export function DashboardPage() {
  return (
    <div className={styles.page}>
      <div className={styles.welcome}><div><Typography.Title level={2}>早上好，运营团队</Typography.Title><Typography.Text type="secondary">这是今天的商城经营与服务概况。</Typography.Text></div><Button type="primary" size="large">导出经营日报</Button></div>
      <Row gutter={[16, 16]}>{metrics.map((item) => <Col xs={24} sm={12} xl={6} key={item.label}><Card className={styles.metricCard}><div className={styles.metricIcon}><CommerceIcon name={item.icon} size={54} /></div><Typography.Text type="secondary">{item.label}</Typography.Text><strong>{item.value}</strong><span>{item.change} 较昨日</span></Card></Col>)}</Row>
      <Row gutter={[16, 16]} className={styles.lower}>
        <Col xs={24} xl={16}><Card title="实时交易趋势" extra={<Typography.Text type="secondary">最近 12 小时</Typography.Text>} className={styles.chartCard}><div className={styles.chart}><div className={styles.chartFill} /><div className={styles.chartLine} /></div><div className={styles.axis}><span>08:00</span><span>12:00</span><span>16:00</span><span>20:00</span></div></Card></Col>
        <Col xs={24} xl={8}><Card title="AI 客服质效" className={styles.aiCard}><div className={styles.aiTitle}><CommerceIcon name="aiSupport" size={68} /><div><strong>1,926</strong><span>今日接待会话</span></div></div><Space orientation="vertical" size={20} style={{ width: '100%' }}><div><div className={styles.progressLabel}><span>自主解决率</span><b>92.8%</b></div><Progress percent={92.8} showInfo={false} /></div><div><div className={styles.progressLabel}><span>满意度</span><b>96.4%</b></div><Progress percent={96.4} showInfo={false} strokeColor="#12b76a" /></div></Space></Card></Col>
      </Row>
      <Card title="最新订单" extra={<Button type="link">查看全部</Button>}><Table rowKey="id" columns={columns} dataSource={orders} pagination={false} scroll={{ x: 640 }} /></Card>
    </div>
  )
}
