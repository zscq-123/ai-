import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { Store } from './data'
import { Icon } from './Icon'
import {
  analyticsDate, categoryNames, datesBetween, earliestSelectableDate, exportCell,
  formatMetric, metricChange, metrics, metricValue, selectRecords, shiftDate, sumRecords,
} from './analytics'
import type { AnalyticsCategory, Metric, MetricKey, Totals } from './analytics'
import './analytics.css'

type Props = { stores: Store[]; scope: string; query: string; onSelectStore: (id: string) => void; onConnectData: () => void }
type SeriesPoint = { date: string; value: number | null }
type AnalyticsView = AnalyticsCategory | 'performance'

export default function AnalyticsPage({ stores, scope, query, onSelectStore, onConnectData }: Props) {
  const [view, setView] = useState<AnalyticsView>('sales')
  const [category, setCategory] = useState<AnalyticsCategory>('sales')
  const [metricKey, setMetricKey] = useState<MetricKey>('revenue')
  const [preset, setPreset] = useState('7')
  const [start, setStart] = useState(shiftDate(analyticsDate, -6))
  const [end, setEnd] = useState(analyticsDate)
  const [customStart, setCustomStart] = useState(shiftDate(analyticsDate, -6))
  const [customEnd, setCustomEnd] = useState(analyticsDate)
  const [error, setError] = useState('')
  const [sortKey, setSortKey] = useState<MetricKey>('revenue')
  const [descending, setDescending] = useState(true)
  const selectedStores = stores.filter(s => (scope === 'all' || scope === s.id) && `${s.name} ${s.platform} ${s.domain}`.toLowerCase().includes(query.toLowerCase()))
  const currentMetrics = metrics[category]
  const metric = currentMetrics.find(m => m.key === metricKey) || currentMetrics[0]
  const dates = datesBetween(start, end)
  const previousEnd = shiftDate(start, -1)
  const previousStart = shiftDate(start, -dates.length)
  const ids = selectedStores.map(s => s.id)
  const records = selectRecords(ids, start, end)
  const previousRecords = selectRecords(ids, previousStart, previousEnd)
  const totals = sumRecords(records)
  const previousTotals = sumRecords(previousRecords)
  const hasData = records.length > 0
  const storeRows = selectedStores.map(store => {
    const rows = records.filter(r => r.storeId === store.id)
    return { store, totals: sumRecords(rows), hasData: rows.length > 0 }
  }).sort((a, b) => {
    const av = a.hasData ? metricValue(a.totals, sortKey) : null
    const bv = b.hasData ? metricValue(b.totals, sortKey) : null
    if (av === null) return bv === null ? 0 : 1
    if (bv === null) return -1
    return (av - bv) * (descending ? -1 : 1)
  })
  const covered = storeRows.filter(r => r.hasData).length
  const daily = dates.map((date, index) => {
    const rows = records.filter(r => r.date === date)
    const previousDate = shiftDate(previousStart, index)
    const previous = previousRecords.filter(r => r.date === previousDate)
    return { date, previousDate, totals: sumRecords(rows), previousTotals: sumRecords(previous), hasData: rows.length > 0, hasPrevious: previous.length > 0 }
  })
  const values: SeriesPoint[] = daily.map(d => ({ date: d.date, value: d.hasData ? metricValue(d.totals, metric.key) : null }))
  const previousValues: SeriesPoint[] = daily.map(d => ({ date: d.previousDate, value: d.hasPrevious ? metricValue(d.previousTotals, metric.key) : null }))

  function choosePreset(value: string) {
    setPreset(value)
    setError('')
    if (value !== 'custom') {
      const nextStart = shiftDate(analyticsDate, 1 - Number(value))
      setStart(nextStart); setEnd(analyticsDate); setCustomStart(nextStart); setCustomEnd(analyticsDate)
    }
  }
  function applyCustom(e: FormEvent) {
    e.preventDefault()
    if (!customStart || !customEnd || customStart > customEnd || customStart < earliestSelectableDate || customEnd > analyticsDate) {
      setError('请选择有效日期，开始日期不能晚于结束日期。'); return
    }
    if (datesBetween(customStart, customEnd).length > 31) { setError('自定义范围最多选择 31 天。'); return }
    setError(''); setStart(customStart); setEnd(customEnd)
  }
  function chooseCategory(value: AnalyticsView) {
    setView(value)
    if (value === 'performance') return
    setCategory(value); setMetricKey(metrics[value][0].key); setSortKey(metrics[value][0].key); setDescending(true)
  }
  function downloadReport() {
    if (view === 'performance') {
      const header = ['开始日期', '结束日期', '店铺', '会话数', '回复率', '1分钟响应率', '平均首次响应', '人工接待', '咨询转化订单', '审批处理量']
      const rows = selectedStores.map(store => {
        const summary = sumRecords(records.filter(record => record.storeId === store.id))
        const replyRate = summary.conversations ? summary.responded / summary.conversations * 100 : 0
        const oneMinuteRate = summary.conversations ? Math.max(0, summary.responded - summary.handoffs * .15) / summary.conversations * 100 : 0
        const firstResponse = summary.responded ? summary.responseSeconds / summary.responded : 0
        return [start, end, store.name, summary.conversations, `${replyRate.toFixed(1)}%`, `${oneMinuteRate.toFixed(1)}%`, `${firstResponse.toFixed(1)}秒`, summary.handoffs, Math.round(summary.orders * .18), Math.round(summary.handoffs * .24)]
      })
      const csv = '\uFEFF' + [header, ...rows].map(row => row.map(exportCell).join(',')).join('\r\n')
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      const link = document.createElement('a'); link.href = url; link.download = `NOVA-客服绩效-${start}-${end}.csv`; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      return
    }
    const raw = (t: Totals, m: Metric, available: boolean) => {
      const v = available ? metricValue(t, m.key) : null
      return v === null ? '' : Number(v.toFixed(m.kind === 'number' ? 0 : 2))
    }
    const header = ['统计类型', '开始日期', '结束日期', '店铺', '平台', '币种', '数据状态', ...currentMetrics.map(m => `${m.label}${m.kind === 'percent' ? '（%）' : m.kind === 'seconds' ? '（秒）' : m.kind === 'money' ? '（元）' : m.kind === 'rating' ? '（满分5）' : ''}`)]
    const rows = storeRows.map(row => [categoryNames[category], start, end, row.store.name, row.store.platform, 'CNY', row.hasData ? '演示统计' : '暂无统计', ...currentMetrics.map(m => raw(row.totals, m, row.hasData))])
    rows.push([categoryNames[category], start, end, '汇总', '', 'CNY', '演示统计', ...currentMetrics.map(m => raw(totals, m, hasData))])
    const csv = '\uFEFF' + [header, ...rows].map(row => row.map(exportCell).join(',')).join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = `NOVA-${categoryNames[category]}-${start}-${end}.csv`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return <div className="nc-analytics">
    <div className="nc-page-title"><div><h1>数据中心</h1><p>查看店铺经营、客服与评价表现，支持按周期与店铺对比。</p></div><button className="nc-btn primary" disabled={!hasData} onClick={downloadReport}><Icon name="file" size={16} />导出报表</button></div>
    <div className="nc-analytics-toolbar">
      <div className="nc-analytics-categories" role="group" aria-label="分析类型">{([...(Object.keys(categoryNames) as AnalyticsCategory[]), 'performance' as const]).map(key => <button key={key} aria-pressed={view === key} className={view === key ? 'active' : ''} onClick={() => chooseCategory(key)}>{key === 'performance' ? '客服绩效' : categoryNames[key]}</button>)}</div>
      <div className="nc-analytics-range"><select aria-label="分析时间范围" value={preset} onChange={e => choosePreset(e.target.value)}><option value="7">近 7 天</option><option value="30">近 30 天</option><option value="custom">自定义日期</option></select><span>{start.replaceAll('-', '/')} – {end.replaceAll('-', '/')}</span></div>
    </div>
    {preset === 'custom' && <form className="nc-custom-range" onSubmit={applyCustom}><label>开始日期<input type="date" required min={earliestSelectableDate} max={analyticsDate} value={customStart} onChange={e => setCustomStart(e.target.value)} /></label><label>结束日期<input type="date" required min={earliestSelectableDate} max={analyticsDate} value={customEnd} onChange={e => setCustomEnd(e.target.value)} /></label><button className="nc-btn" type="submit">应用日期</button>{error && <span role="alert">{error}</span>}</form>}
    {view === 'performance' ? <CustomerServicePerformance stores={selectedStores} records={records} start={start} end={end} onSelectStore={onSelectStore} /> : <><div className="nc-analytics-caption"><span>演示统计 · {covered} 家店铺有数据{selectedStores.length > covered ? `，${selectedStores.length - covered} 家暂无统计` : ''}</span><span>对比上期 {previousStart.slice(5).replace('-', '/')} – {previousEnd.slice(5).replace('-', '/')}</span></div>
    <section className="nc-analytics-metrics" aria-label={`${categoryNames[category]}关键指标`}>{currentMetrics.map(m => {
      const value = hasData ? metricValue(totals, m.key) : null
      const previous = previousRecords.length ? metricValue(previousTotals, m.key) : null
      return <button key={m.key} aria-pressed={metric.key === m.key} className={`nc-analytics-metric ${metric.key === m.key ? 'selected' : ''}`} onClick={() => { setMetricKey(m.key); setSortKey(m.key); setDescending(true) }}><span>{m.label}<Icon name="trend" size={14} /></span><strong>{formatMetric(value, m)}</strong><small>较上期 <b>{metricChange(value, previous, m)}</b></small></button>
    })}</section>
    <section className="nc-panel nc-analytics-chart-panel"><div className="nc-panel-heading"><h2>{metric.label}趋势</h2><div className="nc-analytics-legend"><span><i />本期</span><span><i />上期</span></div></div>{hasData ? <TrendChart key={`${start}-${end}-${metric.key}-${ids.join(',')}`} values={values} previous={previousValues} metric={metric} /> : <div className="nc-empty nc-analytics-empty"><EmptyTrendIllustration /><h3>暂无统计数据</h3><p>{selectedStores.length ? '当前店铺没有历史统计。接入真实数据后将在此展示。' : '没有匹配的店铺，请调整店铺范围或搜索条件。'}</p><button type="button" onClick={onConnectData}>去接入真实数据</button></div>}</section>
    <section className="nc-panel nc-analytics-table-panel"><div className="nc-panel-heading"><h2>店铺对比</h2><span className="nc-muted">点击店铺查看详情</span></div><div className="nc-analytics-table-scroll"><table><thead><tr><th scope="col">店铺</th>{currentMetrics.map(m => <th scope="col" key={m.key} aria-sort={sortKey === m.key ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => { setSortKey(m.key); setDescending(sortKey === m.key ? !descending : true) }}>{m.label}<span>{sortKey === m.key ? descending ? '↓' : '↑' : '↕'}</span></button></th>)}</tr></thead><tbody>{storeRows.map(row => <tr key={row.store.id}><th scope="row"><button className="nc-store-drill" onClick={() => onSelectStore(row.store.id)}>{row.store.name}<Icon name="chevron" size={13} /></button><small>{row.store.platform}{!row.hasData ? ' · 暂无统计' : ''}</small></th>{currentMetrics.map(m => <td key={m.key}>{formatMetric(row.hasData ? metricValue(row.totals, m.key) : null, m)}</td>)}</tr>)}</tbody>{hasData && <tfoot><tr><th scope="row">汇总</th>{currentMetrics.map(m => <td key={m.key}>{formatMetric(metricValue(totals, m.key), m)}</td>)}</tr></tfoot>}</table></div>{!selectedStores.length && <div className="nc-analytics-no-rows">没有符合条件的店铺</div>}</section>
    <details className="nc-analytics-definitions"><summary>统计口径与数据说明</summary><p>固定演示快照截至 {analyticsDate}，统计日期按 Asia/Shanghai 划分。历史样例与收件箱、评论中的本地操作相互独立。所有金额采用人民币演示口径，不代表真实经营结果。</p><p>上期为紧邻本期之前、天数相同的日期区间；比率变化显示百分点，评分变化显示分数，其余指标显示相对变化。汇总比率按原始分子、分母计算，不平均各店铺的百分比。</p><dl>{currentMetrics.map(m => <div key={m.key}><dt>{m.label}</dt><dd>{m.definition}</dd></div>)}</dl></details></>}
  </div>
}

function EmptyTrendIllustration() {
  return <svg className="nc-empty-trend-illustration" viewBox="0 0 96 72" role="img" aria-label="暂无趋势数据">
    <path d="M18 12v46h62" />
    <path d="M26 48 40 35l12 8 20-23" />
    <path d="m64 20 8 0 0 8" />
    <path d="M28 58v4M44 58v4M60 58v4" />
  </svg>
}

function CustomerServicePerformance({ stores, records, start, end, onSelectStore }: { stores: Store[]; records: ReturnType<typeof selectRecords>; start: string; end: string; onSelectStore: (id: string) => void }) {
  const totals = sumRecords(records)
  const percentage = (part: number, whole: number) => whole ? `${(part / whole * 100).toFixed(1)}%` : '—'
  const averageResponse = totals.responded ? totals.responseSeconds / totals.responded : 0
  const oneMinuteResponded = Math.max(0, Math.round(totals.responded - totals.handoffs * .15))
  const fiveMinuteResponded = Math.max(oneMinuteResponded, Math.round(totals.responded - totals.handoffs * .04))
  const tenMinuteResponded = Math.max(fiveMinuteResponded, totals.responded)
  const manualConversations = totals.handoffs
  const recoveredOrders = Math.round(totals.orders * .08)
  const approvalCount = Math.round(totals.handoffs * .24)
  const metricsList = [
    { label: '客户会话', value: totals.conversations.toLocaleString('zh-CN'), note: '在线会话与邮件去重统计', icon: 'chat' as const },
    { label: '会话回复率', value: percentage(totals.responded, totals.conversations), note: `${totals.responded} 个会话已获回复`, icon: 'check' as const },
    { label: '1 分钟响应率', value: percentage(oneMinuteResponded, totals.conversations), note: `${oneMinuteResponded} 个会话在 1 分钟内响应`, icon: 'bolt' as const },
    { label: '平均首次响应', value: totals.responded ? `${averageResponse.toFixed(1)} 秒` : '—', note: '包含 AI 与人工首次回复', icon: 'clock' as const },
  ]
  const storeRows = stores.map(store => {
    const summary = sumRecords(records.filter(record => record.storeId === store.id))
    const firstResponse = summary.responded ? summary.responseSeconds / summary.responded : 0
    return { store, summary, firstResponse, oneMinute: Math.max(0, Math.round(summary.responded - summary.handoffs * .15)), converted: Math.round(summary.orders * .18), approvals: Math.round(summary.handoffs * .24) }
  })
  return <div className="nc-performance">
    <div className="nc-analytics-caption"><span>演示统计 · {stores.length} 家店铺 · {start.replaceAll('-', '/')} – {end.replaceAll('-', '/')}</span><span>按首次响应与人工接待口径汇总</span></div>
    <section className="nc-performance-metrics">{metricsList.map(metric => <article key={metric.label}><span><Icon name={metric.icon} size={17} /></span><div><small>{metric.label}</small><strong>{metric.value}</strong><p>{metric.note}</p></div></article>)}</section>
    <div className="nc-performance-grid">
      <section className="nc-panel nc-response-panel"><div className="nc-panel-heading"><h2>响应时效分布</h2><span className="nc-muted">越快越优</span></div>{[
        { label: '1 分钟内', value: oneMinuteResponded, color: 'blue' },
        { label: '5 分钟内', value: fiveMinuteResponded, color: 'cyan' },
        { label: '10 分钟内', value: tenMinuteResponded, color: 'purple' },
        { label: '30 分钟内', value: totals.responded, color: 'green' },
      ].map(item => <div className="nc-response-row" key={item.label}><span>{item.label}<small>{item.value} 个会话</small></span><div><i className={item.color} style={{ width: percentage(item.value, totals.conversations) }} /></div><strong>{percentage(item.value, totals.conversations)}</strong></div>)}</section>
      <section className="nc-panel nc-performance-summary"><div className="nc-panel-heading"><h2>服务转化与协作</h2><span className="nc-muted">演示口径</span></div><div className="nc-performance-summary-grid"><div><span>人工接待</span><strong>{manualConversations}</strong><small>混合接待中的人工会话</small></div><div><span>咨询转化订单</span><strong>{Math.round(totals.orders * .18)}</strong><small>咨询后完成支付的订单</small></div><div><span>挽回订单</span><strong>{recoveredOrders}</strong><small>触达后恢复支付的订单</small></div><div><span>审批处理量</span><strong>{approvalCount}</strong><small>通过、拒绝与转交合计</small></div></div></section>
    </div>
    <section className="nc-panel nc-analytics-table-panel nc-performance-table"><div className="nc-panel-heading"><h2>店铺客服绩效</h2><span className="nc-muted">点击店铺收窄统计范围</span></div><div className="nc-analytics-table-scroll"><table><thead><tr><th scope="col">店铺</th><th scope="col">会话数</th><th scope="col">回复率</th><th scope="col">1 分钟响应率</th><th scope="col">平均首次响应</th><th scope="col">人工接待</th><th scope="col">咨询转化</th><th scope="col">审批量</th></tr></thead><tbody>{storeRows.map(row => <tr key={row.store.id}><th scope="row"><button className="nc-store-drill" onClick={() => onSelectStore(row.store.id)}>{row.store.name}<Icon name="chevron" size={13} /></button><small>{row.store.platform}</small></th><td>{row.summary.conversations}</td><td>{percentage(row.summary.responded, row.summary.conversations)}</td><td>{percentage(row.oneMinute, row.summary.conversations)}</td><td>{row.summary.responded ? `${row.firstResponse.toFixed(1)} 秒` : '—'}</td><td>{row.summary.handoffs}</td><td>{row.converted}</td><td>{row.approvals}</td></tr>)}</tbody></table></div>{!stores.length && <div className="nc-analytics-no-rows">没有符合条件的店铺</div>}</section>
    <details className="nc-analytics-definitions"><summary>客服绩效口径说明</summary><p>本页面为固定样例数据，用于展示客户服务绩效结构，不代表真实店铺结果。回复率按已获首次回复的会话占比统计；分钟级响应率按首次回复时长分段；咨询转化、挽回订单与审批量为演示推导指标。</p></details>
  </div>
}

function TrendChart({ values, previous, metric }: { values: SeriesPoint[]; previous: SeriesPoint[]; metric: Metric }) {
  const [active, setActive] = useState(values.length - 1)
  const svgRef = useRef<SVGSVGElement>(null)
  const [width, setWidth] = useState(860)
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const observer = new ResizeObserver(entries => { const measured = entries[0]?.contentRect.width; if (measured) setWidth(Math.max(220, Math.round(measured))) })
    observer.observe(svg)
    return () => observer.disconnect()
  }, [])
  const left = width < 480 ? 42 : 62, right = 18, top = 12, bottom = 174
  const labelCount = Math.min(values.length, width < 480 ? 3 : 7)
  const labelIndices = new Set(Array.from({ length: labelCount }, (_, i) => Math.round(i * (values.length - 1) / Math.max(1, labelCount - 1))))
  const maxValue = Math.max(1, ...values.map(p => p.value || 0), ...previous.map(p => p.value || 0))
  const ceiling = metric.kind === 'rating' ? 5 : metric.kind === 'percent' && maxValue > 85 ? 100 : Math.ceil(maxValue * 1.12)
  const x = (index: number) => values.length === 1 ? (width + left - right) / 2 : left + index / (values.length - 1) * (width - left - right)
  const y = (value: number) => bottom - value / ceiling * (bottom - top)
  const path = (points: SeriesPoint[]) => {
    let penDown = false
    return points.map((point, index) => {
      if (point.value === null) { penDown = false; return '' }
      const result = `${penDown ? 'L' : 'M'}${x(index).toFixed(2)} ${y(point.value).toFixed(2)}`
      penDown = true
      return result
    }).join(' ')
  }
  const shortValue = (value: number) => {
    if (metric.kind === 'percent') return `${value.toFixed(0)}%`
    if (metric.kind === 'rating') return value.toFixed(1)
    return value >= 10000 ? `${(value / 10000).toFixed(1)}万` : value >= 1000 ? `${(value / 1000).toFixed(1)}千` : Math.round(value).toString()
  }
  const focused = values[active]
  const compare = previous[active]
  return <div className="nc-analytics-chart"><div className="nc-analytics-chart-reading" aria-live="polite"><span>{focused.date.slice(5).replace('-', '/')}<strong>{formatMetric(focused.value, metric)}</strong></span><span>上期 {compare.date.slice(5).replace('-', '/')}<b>{formatMetric(compare.value, metric)}</b></span></div><svg ref={svgRef} viewBox={`0 0 ${width} 207`} role="group" tabIndex={0} aria-label={`${metric.label}每日趋势，使用左右方向键查看各日数据`} onKeyDown={e => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) { e.preventDefault(); setActive(e.key === 'Home' ? 0 : e.key === 'End' ? values.length - 1 : Math.max(0, Math.min(values.length - 1, active + (e.key === 'ArrowLeft' ? -1 : 1)))) } }}>
      {[0, .5, 1].map(level => <g key={level}><line x1={left} y1={y(ceiling * level)} x2={width - right} y2={y(ceiling * level)} className="nc-trend-grid" /><text x={left - 13} y={y(ceiling * level) + 4} textAnchor="end">{shortValue(ceiling * level)}</text></g>)}
      <path d={path(previous)} className="nc-trend-previous" /><path d={path(values)} className="nc-trend-current" />
      <line x1={x(active)} x2={x(active)} y1={top} y2={bottom} className="nc-trend-guide" />
      {focused.value !== null && <circle cx={x(active)} cy={y(focused.value)} r="4" className="nc-trend-dot" />}
      {values.map((point, index) => <g key={point.date}>{labelIndices.has(index) && <text x={x(index)} y="199" textAnchor="middle">{point.date.slice(5).replace('-', '/')}</text>}<rect x={x(index) - (values.length === 1 ? 100 : (width - left - right) / (values.length - 1) / 2)} width={values.length === 1 ? 200 : (width - left - right) / (values.length - 1)} y={top} height={bottom - top} fill="transparent" onPointerEnter={() => setActive(index)} onPointerDown={() => setActive(index)}><title>{point.date}：{formatMetric(point.value, metric)}</title></rect></g>)}
    </svg><details className="nc-daily-data"><summary>查看每日数据</summary><div className="nc-analytics-table-scroll"><table><thead><tr><th scope="col">日期</th><th scope="col">本期{metric.label}</th><th scope="col">上期日期</th><th scope="col">上期{metric.label}</th></tr></thead><tbody>{values.map((p, i) => <tr key={p.date}><th scope="row">{p.date}</th><td>{formatMetric(p.value, metric)}</td><td>{previous[i].date}</td><td>{formatMetric(previous[i].value, metric)}</td></tr>)}</tbody></table></div></details></div>
}
