import { useEffect, useMemo, useState } from 'react'
import {
  sellerApi,
  mediaUrl,
  type SellerProduct,
  type StoreChannel,
  type StoreConfig,
  type StoreDesign,
  type StoreModule,
  type StoreModuleType,
} from '../../api'

const labels: Record<StoreModuleType, string> = {
  BANNER: '横幅', STORE_INFO: '店铺信息', PRODUCT_GRID: '商品区', ANNOUNCEMENT: '公告', COUPON: '优惠',
}

const createModule = (type: StoreModuleType): StoreModule => ({
  id: `${type.toLowerCase()}-${crypto.randomUUID()}`,
  type,
  visible: true,
  data: type === 'PRODUCT_GRID'
    ? { title: '店铺精选', limit: 6 }
    : type === 'ANNOUNCEMENT'
      ? { text: '请输入店铺公告' }
      : type === 'COUPON'
        ? { title: '限时优惠', description: '填写优惠说明' }
        : type === 'STORE_INFO'
          ? { title: '店铺名称', description: '填写店铺介绍' }
          : { title: '店铺主标题', subtitle: '填写一句简短的介绍', imageUrl: '' },
})

export function StoreDesigner({ merchantId, products, onDirtyChange }: { merchantId: string; products: SellerProduct[]; onDirtyChange: (dirty: boolean) => void }) {
  const [channel, setChannel] = useState<StoreChannel>('WEB')
  const [design, setDesign] = useState<StoreDesign | null>(null)
  const [selectedId, setSelectedId] = useState('')
  const [status, setStatus] = useState('正在读取草稿…')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => { onDirtyChange(dirty || saving) }, [dirty, saving, onDirtyChange])

  useEffect(() => {
    let active = true
    setDesign(null); setStatus('正在读取草稿…')
    sellerApi.storeDesign(merchantId, channel).then((result) => {
      if (!active) return
      setDesign(result); setSelectedId(result.draft.modules[0]?.id ?? ''); setDirty(false)
      setStatus(result.updatedAt ? `草稿 v${result.draftVersion}` : '未保存的新草稿')
    }).catch((reason: unknown) => active && setStatus(reason instanceof Error ? reason.message : '草稿读取失败'))
    return () => { active = false }
  }, [channel, merchantId])

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const config = design?.draft
  const selected = useMemo(() => config?.modules.find((item) => item.id === selectedId), [config, selectedId])
  const updateConfig = (next: StoreConfig) => setDesign((current) => current ? { ...current, draft: next } : current)
  const markDirty = () => { setDirty(true); setStatus('有未保存更改') }
  const switchChannel = (next: StoreChannel) => {
    if (next === channel || saving) return
    if (dirty && !window.confirm('切换终端将放弃当前未保存的更改。')) return
    setChannel(next)
  }
  const updateModule = (id: string, transform: (item: StoreModule) => StoreModule) => {
    if (!config) return
    updateConfig({ ...config, modules: config.modules.map((item) => item.id === id ? transform(item) : item) })
    markDirty()
  }
  const move = (index: number, direction: -1 | 1) => {
    if (!config) return
    const target = index + direction
    if (target < 0 || target >= config.modules.length) return
    const modules = [...config.modules]
    ;[modules[index], modules[target]] = [modules[target], modules[index]]
    updateConfig({ ...config, modules }); markDirty()
  }
  const add = (type: StoreModuleType) => {
    if (!config) return
    const module = createModule(type)
    updateConfig({ ...config, modules: [...config.modules, module] }); setSelectedId(module.id); markDirty()
  }
  const remove = (id: string) => {
    if (!config || config.modules.length === 1) return
    const modules = config.modules.filter((item) => item.id !== id)
    updateConfig({ ...config, modules }); setSelectedId(modules[0]?.id ?? ''); markDirty()
  }
  const save = async () => {
    if (!config) return
    setSaving(true); setStatus('正在保存…')
    try { const result = await sellerApi.saveStoreDesign(merchantId, channel, design?.draftVersion ?? 0, config); setDesign(result); setDirty(false); setStatus(`已保存草稿 v${result.draftVersion}`) }
    catch (reason) { setStatus(reason instanceof Error ? reason.message : '保存失败') }
    finally { setSaving(false) }
  }
  const publish = async () => {
    if (!config) return
    setSaving(true); setStatus('正在发布…')
    try {
      const saved = await sellerApi.saveStoreDesign(merchantId, channel, design?.draftVersion ?? 0, config)
      setDesign(saved); setDirty(false)
      const result = await sellerApi.publishStoreDesign(merchantId, channel)
      setDesign(result); setDirty(false); setStatus(`已发布 v${result.publishedVersion ?? saved.draftVersion}`)
    } catch (reason) { setStatus(reason instanceof Error ? reason.message : '发布失败，请稍后重试。') }
    finally { setSaving(false) }
  }

  return <section className="designer-page">
    <div className="designer-heading"><div><h1>店铺装修</h1><p>编辑草稿不会影响线上店铺，发布后才会更新。</p></div><span>{status}</span></div>
    <div className="designer-toolbar" aria-label="店铺装修工具栏">
      <div className="device-switch" role="group" aria-label="预览终端"><button disabled={saving} className={channel === 'WEB' ? 'active' : ''} onClick={() => switchChannel('WEB')}>网页端</button><button disabled={saving} className={channel === 'MOBILE' ? 'active' : ''} onClick={() => switchChannel('MOBILE')}>移动端</button></div>
      <div className="designer-actions"><a href={`http://127.0.0.1:3001/store/${merchantId}?channel=${channel.toLowerCase()}`} target="_blank" rel="noreferrer">查看已发布页面</a><button disabled={saving || !config} onClick={() => void save()}>保存草稿</button><button className="primary" disabled={saving || !config} onClick={() => void publish()}>发布</button></div>
    </div>
    {!config ? <div className="designer-loading">{status}</div> : <fieldset className="designer-grid" disabled={saving}>
      <aside className="module-library"><h2>页面模块</h2><p>选择模块进行编辑和排序。</p><ol>{config.modules.map((module, index) => <li key={module.id} className={module.id === selectedId ? 'selected' : ''}><button className="module-select" onClick={() => setSelectedId(module.id)}><span>{labels[module.type]}</span><small>{module.visible ? '已显示' : '已隐藏'}</small></button><div className="module-order"><button disabled={index === 0} aria-label="上移" onClick={() => move(index, -1)}>↑</button><button disabled={index === config.modules.length - 1} aria-label="下移" onClick={() => move(index, 1)}>↓</button></div></li>)}</ol><div className="module-add"><span>添加模块</span>{(Object.keys(labels) as StoreModuleType[]).map((type) => <button key={type} onClick={() => add(type)}>+ {labels[type]}</button>)}</div></aside>
      <div className={`store-canvas ${channel.toLowerCase()}`}><div className="canvas-label">{channel === 'WEB' ? 'Web 预览' : '移动端预览'}</div><StorePreview config={config} products={products} /></div>
      <aside className="inspector"><h2>设置</h2><div className="theme-fields"><label>主色<input type="color" value={config.theme.primaryColor} onChange={(event) => { updateConfig({ ...config, theme: { ...config.theme, primaryColor: event.target.value } }); markDirty() }} /></label><label>背景<input type="color" value={config.theme.backgroundColor} onChange={(event) => { updateConfig({ ...config, theme: { ...config.theme, backgroundColor: event.target.value } }); markDirty() }} /></label><label>文字<input type="color" value={config.theme.textColor} onChange={(event) => { updateConfig({ ...config, theme: { ...config.theme, textColor: event.target.value } }); markDirty() }} /></label></div>{selected ? <ModuleInspector module={selected} onChange={(next) => updateModule(selected.id, () => next)} onRemove={() => remove(selected.id)} canRemove={config.modules.length > 1} /> : <p className="inspector-empty">选择一个模块后进行编辑。</p>}</aside>
    </fieldset>}
  </section>
}

function ModuleInspector({ module, onChange, onRemove, canRemove }: { module: StoreModule; onChange: (module: StoreModule) => void; onRemove: () => void; canRemove: boolean }) {
  const setData = (key: string, value: string | number) => onChange({ ...module, data: { ...module.data, [key]: value } })
  return <div className="module-fields"><div className="inspector-title"><b>{labels[module.type]}</b><label className="visibility"><input type="checkbox" checked={module.visible} onChange={(event) => onChange({ ...module, visible: event.target.checked })} />显示</label></div>{module.type !== 'ANNOUNCEMENT' && <label>标题<input value={module.data.title ?? ''} onChange={(event) => setData('title', event.target.value)} /></label>}{module.type === 'BANNER' && <><label>副标题<textarea value={module.data.subtitle ?? ''} onChange={(event) => setData('subtitle', event.target.value)} /></label><label>图片 URL<input inputMode="url" placeholder="https://" value={module.data.imageUrl ?? ''} onChange={(event) => setData('imageUrl', event.target.value)} /></label></>}{(module.type === 'STORE_INFO' || module.type === 'COUPON') && <label>说明<textarea value={module.data.description ?? ''} onChange={(event) => setData('description', event.target.value)} /></label>}{module.type === 'ANNOUNCEMENT' && <label>公告内容<textarea value={module.data.text ?? ''} onChange={(event) => setData('text', event.target.value)} /></label>}{module.type === 'PRODUCT_GRID' && <label>商品数量<input type="number" min="1" max="24" value={module.data.limit ?? 6} onChange={(event) => setData('limit', Number(event.target.value))} /></label>}<button className="remove-module" disabled={!canRemove} onClick={onRemove}>删除模块</button></div>
}

export function StorePreview({ config, products }: { config: StoreConfig; products: SellerProduct[] }) {
  const visible = config.modules.filter((item) => item.visible)
  return <div className="store-preview" style={{ '--store-primary': config.theme.primaryColor, '--store-bg': config.theme.backgroundColor, '--store-text': config.theme.textColor } as React.CSSProperties}>{visible.map((module) => {
    if (module.type === 'BANNER') return <section className="preview-banner" key={module.id} style={module.data.imageUrl ? { backgroundImage: `linear-gradient(90deg, rgba(0,0,0,.58), rgba(0,0,0,.08)), url(${module.data.imageUrl})` } : undefined}><h2>{module.data.title}</h2><p>{module.data.subtitle}</p></section>
    if (module.type === 'STORE_INFO') return <section className="preview-store-info" key={module.id}><span>{(module.data.title ?? '店').slice(0, 1)}</span><div><h2>{module.data.title}</h2><p>{module.data.description}</p></div></section>
    if (module.type === 'ANNOUNCEMENT') return <div className="preview-notice" key={module.id}><b>公告</b><span>{module.data.text}</span></div>
    if (module.type === 'COUPON') return <section className="preview-coupon" key={module.id}><div><small>店铺优惠</small><h2>{module.data.title}</h2><p>{module.data.description}</p></div><span className="coupon-preview-label">优惠展示</span></section>
    const items = products.slice(0, module.data.limit ?? 6)
    return <section className="preview-products" key={module.id}><h2>{module.data.title}</h2><div>{items.map((product) => <article key={product.id}>{product.coverImageUrl ? <img className="designer-product-image" src={mediaUrl(product.coverImageUrl)} alt={product.name} /> : <div className="product-placeholder">暂无图片</div>}<h3>{product.name}</h3><b>{new Intl.NumberFormat('zh-CN', { style: 'currency', currency: product.currency ?? 'CNY' }).format(product.salePrice)}</b></article>)}</div>{items.length === 0 && <p>暂无在售商品</p>}</section>
  })}</div>
}
