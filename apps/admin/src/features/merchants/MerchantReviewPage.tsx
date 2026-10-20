import { Alert, Button, Card, Empty, message, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { commerceApi, type Merchant } from '../../shared/api/commerceApi'

const labels = { PENDING_REVIEW: ['待审核', 'processing'], ACTIVE: ['已启用', 'success'], REJECTED: ['已驳回', 'error'], SUSPENDED: ['已暂停', 'warning'] } as const

export function MerchantReviewPage() {
  const [data, setData] = useState<Merchant[]>([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  async function load() { setLoading(true); setError(''); try { setData(await commerceApi.merchants()) } catch (e) { setError(e instanceof Error ? e.message : '加载失败') } finally { setLoading(false) } }
  useEffect(() => {
    commerceApi.merchants().then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : '加载失败')).finally(() => setLoading(false))
  }, [])
  async function review(id: string, approved: boolean) { try { await commerceApi.reviewMerchant(id, approved, approved ? undefined : '资质信息需补充'); message.success(approved ? '商家已通过审核' : '申请已驳回'); await load() } catch (e) { message.error(e instanceof Error ? e.message : '操作失败') } }
  const columns = [
    { title: '店铺 / 企业', render: (_: unknown, r: Merchant) => <div><Typography.Text strong>{r.storeName}</Typography.Text><br/><Typography.Text type="secondary">{r.legalName}</Typography.Text></div> },
    { title: '联系人', render: (_: unknown, r: Merchant) => <div>{r.contactName}<br/><Typography.Text type="secondary">{r.contactPhone}</Typography.Text></div> },
    { title: '注册号', dataIndex: 'businessLicenseNo' },
    { title: '状态', render: (_: unknown, r: Merchant) => <Tag color={labels[r.status][1]}>{labels[r.status][0]}</Tag> },
    { title: '操作', render: (_: unknown, r: Merchant) => r.status === 'PENDING_REVIEW' ? <Space><Button type="primary" size="small" onClick={() => void review(r.id, true)}>通过</Button><Button danger size="small" onClick={() => void review(r.id, false)}>驳回</Button></Space> : '—' },
  ]
  return <div><div style={{marginBottom:24}}><Typography.Title level={2} style={{margin:0}}>第三方商家审核</Typography.Title><Typography.Text type="secondary">审核企业资质、店铺名称和平台准入状态。</Typography.Text></div>{error && <Alert style={{marginBottom:16}} type="warning" showIcon message={error} description="后台接口默认要求 OIDC 登录；设置 commerce_access_token 后可直接操作。" action={<Button onClick={() => void load()}>重试</Button>} />}<Card><Table rowKey="id" loading={loading} columns={columns} dataSource={data} locale={{emptyText:<Empty description="暂无商家申请"/>}} /></Card></div>
}
