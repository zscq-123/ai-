import { useCallback, useEffect, useState } from 'react'
import { sellerApi, type SellerDashboard } from './api'
import { Marketing, Orders, Overview, Settings, Support } from './features/dashboard/SellerPages'
import { ProductEditor } from './features/products/ProductEditor'
import { ProductList } from './features/products/ProductList'
import { StoreDesigner } from './features/store-design/StoreDesigner'
import { SellerLayout, type PageKey } from './layout/SellerLayout'
import { Empty, Loading } from './shared/ui'

export default function App() {
  const [page, setPage] = useState<PageKey>('overview')
  const [editingProductId, setEditingProductId] = useState<string | null>(null)
  const [merchantId] = useState(() => sellerApi.currentMerchantId())
  const [dashboard, setDashboard] = useState<SellerDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!merchantId) { setLoading(false); return }
    let active = true
    setLoading(true); setError('')
    sellerApi.dashboard(merchantId)
      .then((result) => { if (active) setDashboard(result) })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : '店铺数据加载失败') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [merchantId])

  const refreshDashboard = useCallback(async () => {
    if (!merchantId) return
    try { setDashboard(await sellerApi.dashboard(merchantId)); setError('') }
    catch (reason) { setError(reason instanceof Error ? reason.message : '店铺数据加载失败') }
  }, [merchantId])

  const navigate = (next: PageKey) => {
    if (next === page && !editingProductId) return true
    if (dirty && !window.confirm('有未保存的更改。离开此页将放弃这些更改，确定离开吗？')) return false
    setDirty(false); setEditingProductId(null); setPage(next)
    window.scrollTo({ top: 0, behavior: 'instant' })
    return true
  }
  const editProduct = (id: string) => { setEditingProductId(id); window.scrollTo({ top: 0, behavior: 'instant' }) }

  let content
  if (loading) content = <Loading />
  else if (!merchantId) content = <Empty title="请先登录商户账号" detail="登录后即可管理你的店铺。" />
  else if (!dashboard) content = <Empty title="店铺数据暂不可用" detail="请稍后重试。" />
  else if (page === 'products') content = editingProductId
    ? <ProductEditor key={editingProductId} merchantId={merchantId} productId={editingProductId} storeName={dashboard.merchant.storeName} onCancel={() => { navigate('products') }} onSaved={() => void refreshDashboard()} onDirtyChange={setDirty} />
    : <ProductList products={dashboard.products} onEdit={editProduct} onCreate={() => editProduct('new')} />
  else if (page === 'orders') content = <Orders data={dashboard} />
  else if (page === 'support') content = <Support data={dashboard} />
  else if (page === 'design') content = <StoreDesigner merchantId={merchantId} products={dashboard.products} onDirtyChange={setDirty} />
  else if (page === 'marketing') content = <Marketing />
  else if (page === 'settings') content = <Settings data={dashboard} />
  else content = <Overview data={dashboard} onNavigate={navigate} />

  return <SellerLayout page={page} merchant={dashboard?.merchant} editing={!!editingProductId} onNavigate={navigate}>
    {error && <div className="error-banner" role="alert"><b>数据读取失败</b><span>{error}</span><button onClick={() => void refreshDashboard()}>重试</button></div>}
    {content}
  </SellerLayout>
}
