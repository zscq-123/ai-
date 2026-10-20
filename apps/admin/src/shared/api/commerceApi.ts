const baseUrl = import.meta.env.VITE_COMMERCE_API_URL ?? 'http://localhost:8080'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('commerce_access_token')
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init?.headers } })
  if (!response.ok) throw new Error(response.status === 401 ? '请先连接企业身份服务并登录' : `请求失败 (${response.status})`)
  return response.json() as Promise<T>
}

export type Merchant = { id: string; legalName: string; storeName: string; contactName: string; contactPhone: string; businessLicenseNo: string; status: 'PENDING_REVIEW' | 'ACTIVE' | 'REJECTED' | 'SUSPENDED'; createdAt: string }
export const commerceApi = {
  merchants: () => request<Merchant[]>('/api/merchants'),
  reviewMerchant: (id: string, approved: boolean, reason?: string) => request<Merchant>(`/api/merchants/${id}/review`, { method: 'POST', body: JSON.stringify({ approved, reason }) }),
}
