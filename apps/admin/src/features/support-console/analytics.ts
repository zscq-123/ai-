// Fixed historical fixtures for the prototype. Never represents live commerce data.
export const analyticsDate = '2026-11-13'
export const earliestSelectableDate = '2026-10-01'
export type AnalyticsCategory = 'sales' | 'service' | 'reviews'
export type MetricKey = 'revenue' | 'orders' | 'averageOrder' | 'conversion' | 'conversations' | 'aiRate' | 'responseTime' | 'handoffs' | 'reviews' | 'rating' | 'lowRatingRate' | 'replyRate'
export type Totals = {
  revenueCents: number; orders: number; visitors: number; buyers: number;
  conversations: number; aiResolved: number; handoffs: number; responseSeconds: number; responded: number;
  reviews: number; ratingSum: number; lowReviews: number; repliedReviews: number;
}
export type DailyRecord = Totals & { date: string; storeId: string }
export type Metric = { key: MetricKey; label: string; kind: 'money' | 'number' | 'percent' | 'seconds' | 'rating'; definition: string }
export const categoryNames: Record<AnalyticsCategory, string> = { sales: '经营数据', service: '客服表现', reviews: '评论分析' }
export const metrics: Record<AnalyticsCategory, Metric[]> = {
  sales: [
    { key: 'revenue', label: '支付金额', kind: 'money', definition: '按支付日期统计的订单实付金额，退款未扣除；示例金额统一为人民币，不进行实时汇率换算。' },
    { key: 'orders', label: '支付订单', kind: 'number', definition: '统计期内已支付订单数，不含取消及未支付订单。' },
    { key: 'averageOrder', label: '客单价', kind: 'money', definition: '支付金额 ÷ 支付订单数；按订单口径计算。' },
    { key: 'conversion', label: '支付转化率', kind: 'percent', definition: '支付买家人次 ÷ 访客人次；跨天、跨店铺未去重，按日级人次汇总。' },
  ],
  service: [
    { key: 'conversations', label: '客户会话', kind: 'number', definition: '统计期内新建的在线会话及邮件会话数，同一会话多条消息只计一次。' },
    { key: 'aiRate', label: 'AI 独立解决率', kind: 'percent', definition: '无需转人工且已解决的 AI 会话数 ÷ 客户会话数。' },
    { key: 'responseTime', label: '平均首次响应', kind: 'seconds', definition: '已获回复会话的首次响应秒数之和 ÷ 已获回复会话数，包含 AI 与人工回复。' },
    { key: 'handoffs', label: '转人工会话', kind: 'number', definition: '统计期内新建且转交人工的会话数；已转交不代表已解决。' },
  ],
  reviews: [
    { key: 'reviews', label: '新增评论', kind: 'number', definition: '按评论创建日期统计的商品评论数。' },
    { key: 'rating', label: '平均评分', kind: 'rating', definition: '评分总和 ÷ 评论数，满分 5 分，跨店铺按评论数加权。' },
    { key: 'lowRatingRate', label: '低分评论占比', kind: 'percent', definition: '3 星及以下评论数 ÷ 评论总数。' },
    { key: 'replyRate', label: '评论回复率', kind: 'percent', definition: '统计期内新增且已回复的评论数 ÷ 新增评论数，以演示快照截止时的状态统计。' },
  ],
}
const dayMs = 86_400_000
export function shiftDate(date: string, days: number) { return new Date(Date.parse(`${date}T00:00:00Z`) + days * dayMs).toISOString().slice(0, 10) }
export function datesBetween(start: string, end: string) {
  const count = Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / dayMs) + 1
  return Array.from({ length: Math.max(0, count) }, (_, i) => shiftDate(start, i))
}
export function emptyTotals(): Totals { return { revenueCents: 0, orders: 0, visitors: 0, buyers: 0, conversations: 0, aiResolved: 0, handoffs: 0, responseSeconds: 0, responded: 0, reviews: 0, ratingSum: 0, lowReviews: 0, repliedReviews: 0 } }
export function sumRecords(records: Totals[]): Totals {
  const total = emptyTotals()
  for (const row of records) for (const key of Object.keys(total) as (keyof Totals)[]) total[key] += row[key]
  return total
}
const ratio = (a: number, b: number, scale = 1): number | null => b ? a / b * scale : null
export function metricValue(t: Totals, key: MetricKey): number | null {
  switch (key) {
    case 'revenue': return t.revenueCents / 100
    case 'orders': return t.orders
    case 'averageOrder': return ratio(t.revenueCents / 100, t.orders)
    case 'conversion': return ratio(t.buyers, t.visitors, 100)
    case 'conversations': return t.conversations
    case 'aiRate': return ratio(t.aiResolved, t.conversations, 100)
    case 'responseTime': return ratio(t.responseSeconds, t.responded)
    case 'handoffs': return t.handoffs
    case 'reviews': return t.reviews
    case 'rating': return ratio(t.ratingSum, t.reviews)
    case 'lowRatingRate': return ratio(t.lowReviews, t.reviews, 100)
    case 'replyRate': return ratio(t.repliedReviews, t.reviews, 100)
  }
}
export function formatMetric(value: number | null, metric: Metric) {
  if (value === null) return '—'
  if (metric.kind === 'money') return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  if (metric.kind === 'percent') return `${value.toFixed(1)}%`
  if (metric.kind === 'seconds') return `${value.toFixed(1)} 秒`
  if (metric.kind === 'rating') return `${value.toFixed(2)} / 5`
  return value.toLocaleString('zh-CN')
}
export function metricChange(current: number | null, previous: number | null, metric: Metric) {
  if (current === null || previous === null) return '暂无可比数据'
  const delta = current - previous
  const prefix = delta > 0 ? '+' : delta < 0 ? '−' : ''
  if (metric.kind === 'percent') return `${prefix}${Math.abs(delta).toFixed(1)} 个百分点`
  if (metric.kind === 'rating') return `${prefix}${Math.abs(delta).toFixed(2)} 分`
  if (!previous) return current ? '上期为 0' : '无变化'
  return `${prefix}${(Math.abs(delta / previous) * 100).toFixed(1)}%`
}

export const analyticsRecords: DailyRecord[] = datesBetween('2026-09-01', analyticsDate).flatMap((date, day) =>
  ['s1', 's2', 's3', 's4'].map((storeId, store) => {
    const variation = (day * 17 + store * 23) % 19
    const growth = 1 + day / 500
    const eventLift = date >= '2026-11-09' && date <= '2026-11-11' ? 1.48 : 1
    const orders = Math.round(([34, 24, 19, 28][store] + variation) * growth * eventLift)
    const priceCents = [18900, 13700, 21500, 15900][store] + ((day * 7 + store * 13) % 21) * 100
    const visitors = Math.round(orders * (22 + (day + store) % 9))
    const buyers = Math.round(orders * .94)
    const conversations = Math.round(orders * (.52 + (day % 4) * .05))
    const aiResolved = Math.floor(conversations * (.74 + ((day + store) % 10) / 100))
    const handoffs = Math.floor((conversations - aiResolved) * .8)
    const responded = Math.max(aiResolved + handoffs, conversations - 2)
    const responseSeconds = responded * (4 + store * 2 + ((day + store) % 7))
    const reviews = Math.max(1, Math.round(orders * .28))
    const lowReviews = (day + store) % 8 === 0 ? 2 : (day + store) % 3 === 0 ? 1 : 0
    const fourStar = Math.min(reviews - lowReviews, 2 + (day + store) % 3)
    const ratingSum = lowReviews * 2 + fourStar * 4 + (reviews - lowReviews - fourStar) * 5
    return { date, storeId, revenueCents: orders * priceCents, orders, visitors, buyers, conversations, aiResolved, handoffs, responded, responseSeconds, reviews, ratingSum, lowReviews, repliedReviews: Math.max(0, reviews - 1 - ((day + store) % 3)) }
  }),
)

export function selectRecords(storeIds: string[], start: string, end: string) {
  const ids = new Set(storeIds)
  return analyticsRecords.filter(row => ids.has(row.storeId) && row.date >= start && row.date <= end)
}
export function exportCell(value: string | number) {
  let text = String(value)
  if (/^[\s]*[=+\-@]/.test(text)) text = `'${text}`
  return `"${text.replaceAll('"', '""')}"`
}
