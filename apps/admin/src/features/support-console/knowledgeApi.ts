export type KnowledgeCategory = 'store' | 'platform'
export type KnowledgeSourceType = 'document' | 'table'

export type KnowledgeDocument = {
  id: string
  name: string
  title: string
  category: KnowledgeCategory
  source_type: KnowledgeSourceType
  format: string
  content_type: string
  size_bytes: number
  extracted_chars: number
  rows: number | null
  enabled: boolean
  status: 'ready' | 'needs_attention'
  uploaded_at: string
}

export type KnowledgeDocumentDetail = KnowledgeDocument & {
  preview: string
  preview_truncated: boolean
}

export type ConnectedKnowledgeItem = {
  id: string
  title: string
  kind: 'faq' | 'category' | 'product'
  source: string
  summary: string
  keywords: string[]
  item_count: number | null
  updated_at: string
}

const aiServiceUrl = (import.meta.env.VITE_AI_SERVICE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function payload<T>(response: Response, fallback: string): Promise<T> {
  const body = await response.json().catch(() => null) as { detail?: string } | T | null
  if (!response.ok) {
    throw new Error(body && typeof body === 'object' && 'detail' in body && body.detail ? body.detail : fallback)
  }
  return body as T
}

export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const response = await fetch(`${aiServiceUrl}/v1/knowledge/documents`)
  return payload<KnowledgeDocument[]>(response, '无法读取知识文件。')
}

export async function getKnowledgeDocument(documentId: string): Promise<KnowledgeDocumentDetail> {
  const response = await fetch(`${aiServiceUrl}/v1/knowledge/documents/${encodeURIComponent(documentId)}`)
  return payload<KnowledgeDocumentDetail>(response, '无法读取知识文件内容。')
}

export async function getConnectedKnowledge(): Promise<ConnectedKnowledgeItem[]> {
  const response = await fetch(`${aiServiceUrl}/v1/knowledge/connected`)
  return payload<ConnectedKnowledgeItem[]>(response, '无法读取 BUZUD 商城知识。')
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error(`无法读取文件：${file.name}`))
    reader.onload = () => {
      const value = String(reader.result || '')
      resolve(value.slice(value.indexOf(',') + 1))
    }
    reader.readAsDataURL(file)
  })
}

export async function uploadKnowledgeDocument(
  file: File,
  category: KnowledgeCategory,
): Promise<KnowledgeDocument> {
  if (file.size > 8 * 1024 * 1024) throw new Error(`${file.name} 超过 8 MB`)
  const response = await fetch(`${aiServiceUrl}/v1/knowledge/documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: file.name,
      content_base64: await readFileAsBase64(file),
      content_type: file.type || 'application/octet-stream',
      category,
    }),
  })
  return payload<KnowledgeDocument>(response, `${file.name} 上传失败。`)
}

export async function setKnowledgeDocumentEnabled(
  documentId: string,
  enabled: boolean,
): Promise<KnowledgeDocument> {
  const response = await fetch(`${aiServiceUrl}/v1/knowledge/documents/${encodeURIComponent(documentId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  })
  return payload<KnowledgeDocument>(response, '知识文件状态保存失败。')
}
