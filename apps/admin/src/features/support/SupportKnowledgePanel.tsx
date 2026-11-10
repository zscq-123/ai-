import { Alert, Button, Card, Space, Table, Tag, Typography, Upload } from 'antd'
import { useEffect, useState } from 'react'
import {
  commerceApi,
  type FaqEntry,
  type FaqImportItem,
} from '../../shared/api/commerceApi'

function csvRows(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let value = ''
  let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index]
    if (character === '"' && quoted && text[index + 1] === '"') {
      value += '"'
      index += 1
    } else if (character === '"') {
      quoted = !quoted
    } else if (character === ',' && !quoted) {
      row.push(value.trim())
      value = ''
    } else if ((character === '\n' || character === '\r') && !quoted) {
      if (character === '\r' && text[index + 1] === '\n') index += 1
      row.push(value.trim())
      if (row.some(Boolean)) rows.push(row)
      row = []
      value = ''
    } else {
      value += character
    }
  }
  row.push(value.trim())
  if (row.some(Boolean)) rows.push(row)
  return rows
}

function normalizeItem(raw: unknown, index: number): FaqImportItem {
  if (!raw || typeof raw !== 'object') throw new Error(`第 ${index + 1} 条不是有效对象`)
  const item = raw as Record<string, unknown>
  const question = typeof item.question === 'string' ? item.question.trim() : ''
  const answer = typeof item.answer === 'string' ? item.answer.trim() : ''
  if (!question || !answer) throw new Error(`第 ${index + 1} 条缺少 question 或 answer`)
  const keywords = Array.isArray(item.keywords)
    ? item.keywords.filter((entry): entry is string => typeof entry === 'string')
    : typeof item.keywords === 'string'
      ? item.keywords.split(/[|，,]/).map((entry) => entry.trim()).filter(Boolean)
      : []
  const displayOrder = typeof item.displayOrder === 'number' ? item.displayOrder : (index + 1) * 10
  return { question, answer, keywords, displayOrder }
}

async function parseKnowledgeFile(file: File): Promise<FaqImportItem[]> {
  const text = (await file.text()).replace(/^\uFEFF/, '').trim()
  if (!text) throw new Error('文件内容为空')
  if (file.name.toLowerCase().endsWith('.csv')) {
    const [header, ...rows] = csvRows(text)
    const fields = header.map((value) => value.toLowerCase())
    const questionIndex = fields.indexOf('question')
    const answerIndex = fields.indexOf('answer')
    const keywordsIndex = fields.indexOf('keywords')
    if (questionIndex < 0 || answerIndex < 0) throw new Error('CSV 表头必须包含 question、answer')
    return rows.map((row, index) => normalizeItem({
      question: row[questionIndex],
      answer: row[answerIndex],
      keywords: keywordsIndex >= 0 ? row[keywordsIndex] : '',
      displayOrder: (index + 1) * 10,
    }, index))
  }
  const raw = file.name.toLowerCase().endsWith('.jsonl')
    ? text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line) as unknown)
    : JSON.parse(text) as unknown
  const entries = Array.isArray(raw)
    ? raw
    : raw && typeof raw === 'object' && Array.isArray((raw as { entries?: unknown }).entries)
      ? (raw as { entries: unknown[] }).entries
      : []
  if (!entries.length) throw new Error('文件中没有 FAQ 条目')
  return entries.map(normalizeItem)
}

export function SupportKnowledgePanel() {
  const [entries, setEntries] = useState<FaqEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  async function load() {
    setLoading(true)
    try {
      setEntries(await commerceApi.faqs())
    } catch (error) {
      setNotice({ type: 'error', text: error instanceof Error ? error.message : 'FAQ 读取失败' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    commerceApi.faqs()
      .then((result) => { if (active) setEntries(result) })
      .catch((error: unknown) => {
        if (active) setNotice({ type: 'error', text: error instanceof Error ? error.message : 'FAQ 读取失败' })
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  async function upload(file: File) {
    setLoading(true)
    setNotice(null)
    try {
      const parsed = await parseKnowledgeFile(file)
      setEntries(await commerceApi.importFaqs(parsed))
      setNotice({ type: 'success', text: `已导入 ${parsed.length} 条草稿，审核后点击“发布上线”。` })
    } catch (error) {
      setNotice({ type: 'error', text: error instanceof Error ? error.message : '知识库导入失败' })
    } finally {
      setLoading(false)
    }
  }

  async function publish(id: string) {
    setLoading(true)
    setNotice(null)
    try {
      await commerceApi.publishFaq(id)
      await load()
      setNotice({ type: 'success', text: 'FAQ 已发布到线上客服。' })
    } catch (error) {
      setNotice({ type: 'error', text: error instanceof Error ? error.message : 'FAQ 发布失败' })
      setLoading(false)
    }
  }

  return <Card title="FAQ 知识库" extra={<Typography.Text type="secondary">客服主管导入 · 运营审核发布</Typography.Text>}>
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      {notice && <Alert showIcon type={notice.type} message={notice.text} closable onClose={() => setNotice(null)} />}
      <Upload.Dragger accept=".json,.jsonl,.csv" showUploadList={false} beforeUpload={(file) => { void upload(file); return false }} disabled={loading}>
        <p><strong>上传 FAQ 知识文件</strong></p>
        <p>支持 JSON、JSONL、CSV；字段为 question、answer、keywords。单次最多 200 条。</p>
      </Upload.Dragger>
      <Table<FaqEntry> rowKey="id" loading={loading} dataSource={entries} pagination={{ pageSize: 6 }} columns={[
        { title: '常见问题', dataIndex: 'question', width: '28%' },
        { title: '标准回答', dataIndex: 'answer', ellipsis: true },
        { title: '关键词', dataIndex: 'keywords', render: (values: string[]) => values.map((value) => <Tag key={value}>{value}</Tag>) },
        { title: '状态', dataIndex: 'status', render: (value: FaqEntry['status']) => <Tag color={value === 'PUBLISHED' ? 'success' : value === 'DRAFT' ? 'warning' : 'default'}>{value === 'PUBLISHED' ? '已发布' : value === 'DRAFT' ? '待审核' : '历史版本'}</Tag> },
        { title: '操作', render: (_, row) => <Button type="link" disabled={row.status !== 'DRAFT'} onClick={() => void publish(row.id)}>{row.status === 'PUBLISHED' ? '线上生效' : row.status === 'ARCHIVED' ? '已归档' : '发布上线'}</Button> },
      ]} />
    </Space>
  </Card>
}
