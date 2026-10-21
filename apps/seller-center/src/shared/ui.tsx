import type { ReactNode } from 'react'

export const iconPath = (name: string, size = 96) => `/brand/icons/image2.5/${size}/${name}-red.png`
export const money = (value: number, currency = 'CNY') => new Intl.NumberFormat('zh-CN', { style: 'currency', currency }).format(value)
export const statusText = (status: string) => ({ ACTIVE: '在售', DRAFT: '草稿', ARCHIVED: '已下架', PAID: '待发货', FULFILLING: '备货中', SHIPPED: '已发货', COMPLETED: '已完成', RESOLVED: '已解决', HANDED_OFF: '已转人工', OPEN: '进行中' }[status] ?? status)

export function PageTitle({ title, detail, actions }: { title: string; detail: string; actions?: ReactNode }) {
  return <div className="page-title"><div><h1>{title}</h1><p>{detail}</p></div>{actions && <div className="page-actions">{actions}</div>}</div>
}

export function Loading({ label = '正在读取店铺数据…' }: { label?: string }) {
  return <div className="loading" role="status"><i /><span>{label}</span></div>
}

export function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="empty"><img src={iconPath('store', 256)} alt="" /><h1>{title}</h1><p>{detail}</p></div>
}

export function Table({ headers, rows, empty }: { headers: string[]; rows: string[][]; empty: string }) {
  return <div className="table-wrap"><table><thead><tr>{headers.map((item) => <th key={item}>{item}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={`${row[0]}-${index}`}>{row.map((cell, cellIndex) => <td key={`${cell}-${cellIndex}`}>{cell}</td>)}</tr>)}</tbody></table>{rows.length === 0 && <div className="table-empty">{empty}</div>}</div>
}
