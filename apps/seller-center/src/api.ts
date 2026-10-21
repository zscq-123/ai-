const commerceBaseUrl = import.meta.env.VITE_COMMERCE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('commerce_access_token')
  const response = await fetch(`${commerceBaseUrl}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    if (response.status === 409) throw new Error('商品或草稿已被更新，请重新载入后再保存。当前编辑内容仍保留。')
    if (response.status === 401) throw new Error('登录已过期，请重新登录商户账号。')
    if (response.status === 403) throw new Error('当前账号没有操作此店铺的权限。')
    const detail = await response.json().catch(() => null) as { detail?: string; message?: string } | null
    throw new Error(detail?.detail ?? detail?.message ?? `请求未完成（${response.status}），请稍后重试。`)
  }
  return response.json() as Promise<T>
}

export type Merchant = { id: string; storeName: string; legalName: string; status: string }
export type SellerOrder = { id: string; orderNo: string; customerName: string; totalAmount: number; status: string; createdAt: string }
export type SellerProduct = { id: string; name: string; skuCode: string; salePrice: number; availableStock: number; status: string; updatedAt: string; coverImageUrl?: string | null; imageUrls?: string[]; currency?: string; categoryName?: string | null }
export type SellerProductDetail = SellerProduct & {
  merchantId: string; categoryId: string; subtitle: string | null; brand: string | null
  description: string | null; weightKg: number | null; skuId: string; skuTitle: string
  marketPrice: number | null; version: number; imageUrls: string[]; createdAt: string
}
export type ProductUpdate = {
  expectedVersion: number; categoryId: string; name: string; subtitle: string; brand: string
  description: string; weightKg: number; skuCode: string; skuTitle: string; salePrice: number
  marketPrice: number; availableStock: number; imageUrls: string[]
}
export type UploadedImage = { id: string; url: string; contentType: string; width: number; height: number; sizeBytes: number }
export type Category = { id: string; parentId: string | null; name: string; slug: string }

export function mediaUrl(url: string) {
  return url.startsWith('/api/') ? `${commerceBaseUrl}${url}` : url
}

function uploadProductImage(merchantId: string, file: File, onProgress: (progress: number) => void): Promise<UploadedImage> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${commerceBaseUrl}/api/seller/${merchantId}/media/product-images`)
    const token = localStorage.getItem('commerce_access_token')
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)
    request.timeout = 60000
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100))
    }
    request.onerror = () => reject(new Error('网络连接中断，请重试。'))
    request.ontimeout = () => reject(new Error('上传超时，请检查网络后重试。'))
    request.onload = () => {
      let result: UploadedImage & { detail?: string; message?: string }
      try { result = JSON.parse(request.responseText) as typeof result }
      catch { reject(new Error('上传未完成，请稍后重试。')); return }
      if (request.status >= 200 && request.status < 300) resolve(result)
      else reject(new Error(result.detail ?? result.message ?? `图片上传失败（${request.status}）`))
    }
    const form = new FormData()
    form.append('file', file)
    request.send(form)
  })
}
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
  product: (merchantId: string, productId: string) => request<SellerProductDetail>(`/api/seller/${merchantId}/products/${productId}`),
  updateProduct: (merchantId: string, productId: string, product: ProductUpdate) =>
    request<SellerProductDetail>(`/api/seller/${merchantId}/products/${productId}`, { method: 'PUT', body: JSON.stringify(product) }),
  createProduct: (merchantId: string, product: Omit<ProductUpdate, 'expectedVersion'>) =>
    request<SellerProductDetail>(`/api/seller/${merchantId}/products`, { method: 'POST', body: JSON.stringify(product) }),
  categories: () => request<Category[]>('/api/public/categories'),
  uploadProductImage,
  storeDesign: (merchantId: string, channel: StoreChannel) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/draft`),
  saveStoreDesign: (merchantId: string, channel: StoreChannel, expectedVersion: number, config: StoreConfig) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/draft`, {
      method: 'PUT', body: JSON.stringify({ expectedVersion, config }),
    }),
  publishStoreDesign: (merchantId: string, channel: StoreChannel) =>
    request<StoreDesign>(`/api/seller/${merchantId}/store-design/${channel}/publish`, { method: 'POST' }),
}
