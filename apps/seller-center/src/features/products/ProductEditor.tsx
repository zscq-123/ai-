import { useEffect, useState, type FormEvent } from 'react'
import { mediaUrl, sellerApi, type Category, type ProductUpdate, type SellerProductDetail } from '../../api'
import { Loading, money, PageTitle, statusText } from '../../shared/ui'
import { ProductImages } from './ProductImages'

type ProductForm = Omit<ProductUpdate, 'expectedVersion'>
const emptyForm: ProductForm = { categoryId: '', name: '', subtitle: '', brand: '', description: '', weightKg: 0, skuCode: '', skuTitle: '', salePrice: 0, marketPrice: 0, availableStock: 0, imageUrls: [] }
const fromProduct = (product: SellerProductDetail): ProductForm => ({ categoryId: product.categoryId, name: product.name, subtitle: product.subtitle ?? '', brand: product.brand ?? '', description: product.description ?? '', weightKg: product.weightKg ?? 0, skuCode: product.skuCode, skuTitle: product.skuTitle, salePrice: product.salePrice, marketPrice: product.marketPrice ?? 0, availableStock: product.availableStock, imageUrls: product.imageUrls ?? [] })
const sections = [['basic', '基本信息'], ['attributes', '商品属性'], ['description', '商品描述'], ['sales', '销售资料'], ['shipping', '物流信息']]

export function ProductEditor({ merchantId, productId, storeName, onCancel, onSaved, onDirtyChange }: {
  merchantId: string; productId: string; storeName: string; onCancel: () => void; onSaved: () => void; onDirtyChange: (dirty: boolean) => void
}) {
  const [product, setProduct] = useState<SellerProductDetail | null>(null)
  const [form, setForm] = useState<ProductForm>(emptyForm)
  const [savedForm, setSavedForm] = useState(JSON.stringify(emptyForm))
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [categoryError, setCategoryError] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [reload, setReload] = useState(0)
  const [activeSection, setActiveSection] = useState('basic')
  const dirty = savedForm !== JSON.stringify(form)

  useEffect(() => {
    let active = true
    setLoading(true); setLoadError(''); setProduct(null); setNotice(''); setCategoryError('')
    sellerApi.categories().then((result) => { if (active) setCategories(result) }).catch(() => { if (active) setCategoryError('分类暂时加载失败。已有商品可保留原分类保存。') })
    const load = async () => {
      try {
        const detail = productId === 'new' ? null : await sellerApi.product(merchantId, productId)
        if (!active) return
        const next = detail ? fromProduct(detail) : { ...emptyForm, imageUrls: [] }
        setProduct(detail); setForm(next); setSavedForm(JSON.stringify(next))
      } catch (reason) { if (active) setLoadError(reason instanceof Error ? reason.message : '商品加载失败。') }
      finally { if (active) setLoading(false) }
    }
    void load()
    return () => { active = false }
  }, [merchantId, productId, reload])

  useEffect(() => { onDirtyChange(dirty || uploading) }, [dirty, uploading, onDirtyChange])
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty || uploading) event.preventDefault() }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty, uploading])

  const update = <K extends keyof ProductForm>(key: K, value: ProductForm[K]) => { setForm((current) => ({ ...current, [key]: value })); setNotice('') }
  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saving || uploading) return
    if (![form.name, form.skuCode, form.skuTitle].every((value) => value.trim())) { setError('请填写商品名称、SKU 编码和规格名称。'); return }
    setSaving(true); setError(''); setNotice('')
    try {
      const data = { ...form, name: form.name.trim(), skuCode: form.skuCode.trim(), skuTitle: form.skuTitle.trim() }
      const result = product
        ? await sellerApi.updateProduct(merchantId, product.id, { ...data, expectedVersion: product.version })
        : await sellerApi.createProduct(merchantId, data)
      const next = fromProduct(result)
      setProduct(result); setForm(next); setSavedForm(JSON.stringify(next)); onDirtyChange(false)
      setNotice(product ? '商品信息已保存。' : '商品已保存为草稿。'); onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : '保存失败，请重试。') }
    finally { setSaving(false) }
  }
  if (loading) return <Loading label="正在读取商品信息…" />
  if (loadError) return <section className="panel editor-load-error" role="alert"><h1>商品暂时无法打开</h1><p>{loadError}</p><button className="secondary-button" onClick={() => setReload((current) => current + 1)}>重新加载</button><button className="text-button" onClick={onCancel}>返回商品列表</button></section>

  const currency = product?.currency ?? 'CNY'
  const selectedCategory = categories.find((category) => category.id === form.categoryId)
  return <div className="product-editor"><PageTitle title={product ? '编辑商品' : '添加商品'} detail={product ? `${statusText(product.status)} · 上次更新 ${new Date(product.updatedAt).toLocaleString('zh-CN')}` : '完善商品信息后保存为草稿。'} actions={<button className="secondary-button" type="button" onClick={onCancel}>返回商品列表</button>} />
    <form onSubmit={(event) => void save(event)}><div className="product-editor-layout"><div className="product-editor-main"><nav className="editor-sections" aria-label="商品信息分区">{sections.map(([id, label]) => <a className={activeSection === id ? 'active' : ''} aria-current={activeSection === id ? 'location' : undefined} onClick={() => setActiveSection(id)} href={`#product-${id}`} key={id}>{label}</a>)}</nav>
      <fieldset className="product-fields" disabled={saving}>
        <section className="panel editor-section" id="product-basic"><h2>基本信息</h2><ProductImages merchantId={merchantId} imageUrls={form.imageUrls} disabled={saving} onChange={(urls) => update('imageUrls', urls)} onBusyChange={setUploading} /><label className="editor-field"><span>商品名称 <em>*</em></span><div className="input-with-count"><input required maxLength={120} placeholder="输入商品名称，包含品牌、品名和关键规格" value={form.name} onChange={(event) => update('name', event.target.value)} /><small>{form.name.length}/120</small></div></label><label className="editor-field"><span>商品副标题</span><input maxLength={240} placeholder="补充商品卖点或适用场景" value={form.subtitle} onChange={(event) => update('subtitle', event.target.value)} /></label><label className="editor-field"><span>商品分类 <em>*</em></span><select required value={form.categoryId} onChange={(event) => update('categoryId', event.target.value)}><option value="">选择商品分类</option>{form.categoryId && !selectedCategory && <option value={form.categoryId}>当前商品分类</option>}{categories.map((category) => <option value={category.id} key={category.id}>{category.parentId ? '　' : ''}{category.name}</option>)}</select></label>{categoryError && <p className="field-hint">{categoryError}</p>}</section>
        <section className="panel editor-section" id="product-attributes"><h2>商品属性</h2><label className="editor-field"><span>品牌</span><input maxLength={80} placeholder="填写商品品牌" value={form.brand} onChange={(event) => update('brand', event.target.value)} /></label></section>
        <section className="panel editor-section" id="product-description"><h2>商品描述</h2><label className="editor-field"><span>详情描述</span><textarea rows={7} maxLength={5000} placeholder="介绍商品的材质、功能、规格及使用方式。" value={form.description} onChange={(event) => update('description', event.target.value)} /><small className="character-count">{form.description.length} / 5000</small></label></section>
        <section className="panel editor-section" id="product-sales"><h2>销售资料</h2><p className="section-description">设置当前商品的销售规格、价格与可售库存。</p><div className="form-grid"><label className="editor-field"><span>SKU 编码 <em>*</em></span><input required maxLength={80} placeholder="店铺内部商品编码" value={form.skuCode} onChange={(event) => update('skuCode', event.target.value)} /></label><label className="editor-field"><span>规格名称 <em>*</em></span><input required maxLength={160} placeholder="例如：白色 / 标准版" value={form.skuTitle} onChange={(event) => update('skuTitle', event.target.value)} /></label><label className="editor-field"><span>销售价格（{currency}）<em>*</em></span><input required type="number" inputMode="decimal" min={0} step="0.01" value={form.salePrice} onChange={(event) => update('salePrice', Number(event.target.value))} /></label><label className="editor-field"><span>市场价格（{currency}）</span><input type="number" inputMode="decimal" min={0} step="0.01" value={form.marketPrice} onChange={(event) => update('marketPrice', Number(event.target.value))} /></label><label className="editor-field"><span>可售库存 <em>*</em></span><input required type="number" inputMode="numeric" min={0} max={2147483647} step={1} value={form.availableStock} onChange={(event) => update('availableStock', Number(event.target.value))} /></label></div></section>
        <section className="panel editor-section" id="product-shipping"><h2>物流信息</h2><label className="editor-field"><span>商品重量（kg）</span><input type="number" inputMode="decimal" min={0} step="0.001" value={form.weightKg} onChange={(event) => update('weightKg', Number(event.target.value))} /></label><p className="field-hint">填写包含包装的商品重量。</p></section>
      </fieldset>
    </div><ProductPreview form={form} storeName={storeName} currency={currency} /></div>
    <div className="editor-savebar"><div className="save-feedback" role="status" aria-live="polite">{error ? <span className="inline-error">{error}</span> : notice ? <span className="success-message">{notice}</span> : <span>{uploading ? '图片上传中，请稍候…' : dirty ? '有未保存的更改' : '更改已保存'}{form.imageUrls.length === 0 && !uploading ? ' · 添加商品图片，让买家更了解商品' : ''}</span>}</div><div><button className="secondary-button" type="button" disabled={saving || uploading} onClick={onCancel}>取消</button><button className="primary-button" type="submit" disabled={saving || uploading || (!dirty && !!product)}>{saving ? '正在保存…' : product ? '保存更改' : '保存草稿'}</button></div></div></form>
  </div>
}

function ProductPreview({ form, storeName, currency }: { form: ProductForm; storeName: string; currency: string }) {
  const [selected, setSelected] = useState(0)
  const index = Math.min(selected, Math.max(0, form.imageUrls.length - 1))
  return <aside className="buyer-preview"><div className="preview-heading"><h2>买家预览</h2><span>移动端</span></div><div className="buyer-preview-card"><div className="buyer-preview-image">{form.imageUrls[index] ? <img src={mediaUrl(form.imageUrls[index])} alt="商品买家预览" /> : <div className="no-product-image"><span>商品图片</span><small>上传后在此展示</small></div>}{form.imageUrls.length > 1 && <><button type="button" className="preview-previous" aria-label="预览上一张图片" onClick={() => setSelected((index + form.imageUrls.length - 1) % form.imageUrls.length)}>‹</button><button type="button" className="preview-next" aria-label="预览下一张图片" onClick={() => setSelected((index + 1) % form.imageUrls.length)}>›</button><small className="preview-image-count">{index + 1}/{form.imageUrls.length}</small></>}</div><div className="buyer-product-info"><strong>{money(form.salePrice, currency)}</strong>{form.marketPrice > form.salePrice && <del>{money(form.marketPrice, currency)}</del>}<h3>{form.name || '商品名称'}</h3>{form.subtitle && <p>{form.subtitle}</p>}<div className="buyer-specification"><span>规格</span><b>{form.skuTitle || '规格名称'}</b><span aria-hidden="true">›</span></div></div><div className="buyer-store"><span>{storeName.slice(0, 1)}</span><b>{storeName}</b></div><div className="buyer-description"><b>商品详情</b><p>{form.description || '填写商品描述后，可在这里查看展示效果。'}</p></div><div className="buyer-preview-actions" aria-hidden="true"><span>客服</span><span>加入购物车</span></div></div><p className="preview-footnote">预览会随编辑内容更新，保存后应用到商品。</p></aside>
}
