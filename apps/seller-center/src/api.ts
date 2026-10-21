const commerceBaseUrl = import.meta.env.VITE_COMMERCE_API_URL ?? 'http://127.0.0.1:8080'

async function request<T>(path: string): Promise<T> {
  const token = localStorage.getItem('commerce_access_token')
  const response = await fetch(`${commerceBaseUrl}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined })
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

export const sellerApi = {
  merchants: async () => {
    try { return await request<Merchant[]>('/api/seller/merchants') }
    catch { return (await request<Merchant[]>('/api/merchants')).filter((merchant) => merchant.status === 'ACTIVE') }
  },
  dashboard: (merchantId: string) => request<SellerDashboard>(`/api/seller/${merchantId}/dashboard`),
}
