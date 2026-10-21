const commerceBaseUrl = import.meta.env.VITE_COMMERCE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('commerce_access_token')
  const response = await fetch(`${commerceBaseUrl}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) throw new Error(`接口请求失败（${response.status}）`)
  return response.json() as Promise<T>
}

export type Merchant = { id: string; storeName: string; legalName: string; status: string }
export type SellerOrder = { id: string; orderNo: string; customerName: string; totalAmount: number; status: string; createdAt: string }
export type SellerProduct = { id: string; name: string; skuCode: string; salePrice: number; availableStock: number; status: string; updatedAt: string }
export type SellerConversation = { id: string; status: string; startedAt: string; handedOffAt: string | null; messageCount: number; lastIntent: string | null }
export type SellerDashboard = {
  generatedAt: string
  merchant: Merchant
  metrics: { todayRevenue: number; pendingFulfillment: number; activeProducts: number; lowStockProducts: number }
  support: { conversationsToday: number; resolvedToday: number; handedOffToday: number; resolutionRate: number; satisfactionRate: number }
  recentOrders: SellerOrder[]
  products: SellerProduct[]
  conversations: SellerConversation[]
}

export type StoreChannel = 'WEB' | 'MOBILE'
export type StoreModuleType = 'BANNER' | 'STORE_INFO' | 'PRODUCT_GRID' | 'ANNOUNCEMENT' | 'COUPON'
export type StoreModule = {
  id: string
  type: StoreModuleType
  visible: boolean
  data: { title?: string; subtitle?: string; description?: string; text?: string; imageUrl?: string; limit?: number }
}
export type StoreConfig = {
  theme: { primaryColor: string; backgroundColor: string; textColor: string }
  modules: StoreModule[]
}
export type StoreDesign = {
  merchantId: string
  channel: StoreChannel
  draftVersion: number
  publishedVersion: number | null
  draft: StoreConfig
  published: StoreConfig | null
  updatedAt: string | null
  publishedAt: string | null
}

function merchantIdFromToken() {
  const token = localStorage.getItem('commerce_access_token')
  if (!token) return ''
  try {
    const payload = token.split('.')[1]
    if (!payload) return ''
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const claims = JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '='))) as { merchant_id?: unknown }
    return typeof claims.merchant_id === 'string' ? claims.merchant_id : ''
  } catch { return '' }
}

export const sellerApi = {
  currentMerchantId: () => merchantIdFromToken()
    || import.meta.env.VITE_SELLER_MERCHANT_ID
    || (import.meta.env.DEV ? '20000000-0000-0000-0000-000000000001' : ''),
  dashboard: (merchantId: string) => request<SellerDashboard>(`/api/seller/${merchantId}/dashboard`),
  storeDesign: (merchantId: string, channel: StoreChannel) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/draft`),
  saveStoreDesign: (merchantId: string, channel: StoreChannel, expectedVersion: number, config: StoreConfig) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/draft`, {
      method: 'PUT', body: JSON.stringify({ expectedVersion, config }),
    }),
  publishStoreDesign: (merchantId: string, channel: StoreChannel) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/publish`, { method: 'POST' }),
}
