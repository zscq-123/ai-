const baseUrl = import.meta.env.VITE_COMMERCE_API_URL ?? 'http://localhost:8080'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('commerce_access_token')
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init?.headers } })
  if (!response.ok) throw new Error(response.status === 401 ? '请先连接企业身份服务并登录' : `请求失败 (${response.status})`)
  return response.json() as Promise<T>
}

export type Merchant = { id: string; legalName: string; storeName: string; contactName: string; contactPhone: string; businessLicenseNo: string; status: 'PENDING_REVIEW' | 'ACTIVE' | 'REJECTED' | 'SUSPENDED'; createdAt: string }
export type OrderSummary = { id: string; orderNo: string; customerId: string; customerName: string; customerEmail: string | null; totalAmount: number; status: string; createdAt: string }
export type ProductSummary = { id: string; version: number; name: string; subtitle: string | null; brand: string | null; description: string | null; weightKg: number | null; status: string; merchantName: string; categoryName: string | null; categoryId: string | null; skuCode: string; skuTitle: string; salePrice: number; marketPrice: number | null; availableStock: number; updatedAt: string }
export type UpdatedProduct = { id: string; version: number }
export type CustomerSummary = { id: string; displayName: string; email: string; status: string; createdAt: string; lastLoginAt: string | null; orderCount: number; totalSpend: number }
export type RevenuePoint = { bucket: string; amount: number }
export type OperationsDashboard = {
  generatedAt: string
  metrics: { todayRevenue: number; yesterdayRevenue: number; pendingFulfillment: number; newCustomers: number; activeProducts: number; pendingMerchants: number }
  support: { conversationsToday: number; resolvedToday: number; handedOffToday: number; resolutionRate: number; satisfactionRate: number }
  revenueTrend: RevenuePoint[]
  recentOrders: OrderSummary[]
  products: ProductSummary[]
  customers: CustomerSummary[]
}
export const commerceApi = {
  dashboard: () => request<OperationsDashboard>('/api/admin/operations/dashboard'),
  orders: () => request<OrderSummary[]>('/api/admin/operations/orders'),
  products: () => request<ProductSummary[]>('/api/admin/operations/products'),
  updateProduct: (id: string, product: { expectedVersion: number; categoryId: string; name: string; subtitle: string; brand: string; description: string; weightKg: number; skuCode: string; skuTitle: string; salePrice: number; marketPrice: number; availableStock: number }) => request<UpdatedProduct>(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(product) }),
  customers: () => request<CustomerSummary[]>('/api/admin/operations/customers'),
  merchants: () => request<Merchant[]>('/api/merchants'),
  reviewMerchant: (id: string, approved: boolean, reason?: string) => request<Merchant>(`/api/merchants/${id}/review`, { method: 'POST', body: JSON.stringify({ approved, reason }) }),
}
