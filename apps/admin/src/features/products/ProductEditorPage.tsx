import {
  Alert,
  Button,
  Checkbox,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { commerceApi, type ProductSummary } from '../../shared/api/commerceApi'
import styles from './productEditor.module.css'

type ProductDraft = {
  name: string
  subtitle: string
  category: string
  brand: string
  price: number
  marketPrice: number
  stock: number
  weight: number
  description: string
  sellerSku: string
}

const emptyDraft: ProductDraft = {
  name: '',
  subtitle: '',
  category: '',
  brand: '',
  price: 0,
  marketPrice: 0,
  stock: 0,
  weight: 0,
  description: '',
  sellerSku: '',
}

const sections = [
  ['basic', '基本信息'],
  ['attributes', '商品属性'],
  ['sales', '销售资料'],
  ['description', '商品描述'],
  ['shipping', '运费与物流'],
  ['marketing', '营销设置'],
] as const

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export function ProductEditorPage() {
  const [draft, setDraft] = useState(emptyDraft)
  const [savedDraft, setSavedDraft] = useState(emptyDraft)
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [productId, setProductId] = useState('')
  const [productVersion, setProductVersion] = useState(0)
  const [categoryId, setCategoryId] = useState('')
  const [skuTitle, setSkuTitle] = useState('')
  const [storeName, setStoreName] = useState('')
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(true)
  const [images, setImages] = useState<string[]>([])
  const [activeSection, setActiveSection] = useState('basic')
  const [saveState, setSaveState] = useState('所有更改已保存')
  const fileInputRef = useRef<HTMLInputElement>(null)

  function applyProduct(product: ProductSummary) {
    const next = {
      ...emptyDraft,
      name: product.name,
      subtitle: product.subtitle ?? '',
      category: product.categoryName ?? '未分类',
      brand: product.brand ?? '',
      price: Number(product.salePrice),
      marketPrice: Number(product.marketPrice ?? product.salePrice),
      stock: product.availableStock,
      weight: Number(product.weightKg ?? 0),
      description: product.description ?? '',
      sellerSku: product.skuCode,
    }
    setProductId(product.id)
    setProductVersion(product.version)
    setCategoryId(product.categoryId ?? '')
    setSkuTitle(product.skuTitle)
    setStoreName(product.merchantName)
    setDraft(next)
    setSavedDraft(next)
    setSaveState('已加载数据库中的商品资料')
  }

  useEffect(() => {
    commerceApi.products().then((items) => { setProducts(items); if (items[0]) applyProduct(items[0]) }).catch((reason: unknown) => setLoadError(reason instanceof Error ? reason.message : '商品数据加载失败')).finally(() => setLoading(false))
  }, [])

  const score = useMemo(() => {
    const checks = [draft.name, draft.subtitle, draft.category, draft.brand, draft.description, draft.price, draft.stock]
    return Math.min(100, Math.round((checks.filter(Boolean).length / checks.length) * 75 + Math.min(images.length, 5) * 5))
  }, [draft, images.length])

  function update<K extends keyof ProductDraft>(key: K, value: ProductDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
    setSaveState('有未保存的更改')
  }

  function addImages(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []).slice(0, Math.max(0, 9 - images.length))
    for (const file of files) {
      if (!file.type.startsWith('image/') || file.size > 5 * 1024 * 1024) continue
      const reader = new FileReader()
      reader.onload = () => setImages((current) => [...current, String(reader.result)].slice(0, 9))
      reader.readAsDataURL(file)
    }
    event.target.value = ''
    setSaveState('有未保存的更改')
  }

  async function save(label: string) {
    if (!productId || !categoryId) { message.error('商品或类目信息不完整，无法保存'); return }
    try {
      const updated = await commerceApi.updateProduct(productId, { expectedVersion: productVersion, categoryId, name: draft.name, subtitle: draft.subtitle, brand: draft.brand, description: draft.description, weightKg: draft.weight, skuCode: draft.sellerSku, skuTitle, salePrice: draft.price, marketPrice: draft.marketPrice, availableStock: draft.stock })
      setProductVersion(updated.version)
      setSavedDraft(draft)
      setSaveState(`${label}成功 · 数据库已更新`)
      message.success(`${label}成功`)
    } catch (reason) {
      message.error(reason instanceof Error ? reason.message : '保存失败')
    }
  }

  function cancelChanges() {
    setDraft(savedDraft)
    setSaveState('所有更改已保存')
  }

  const cover = images[0] ?? '/brand/icons/image2.5/256/package-red.png'

  if (loading) return <Typography.Text>正在从数据库读取商品…</Typography.Text>
  if (loadError) return <Alert type="error" showIcon message="商品数据加载失败" description={loadError} />
  if (!productId) return <Alert type="info" showIcon message="数据库中暂无可编辑商品" />

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <Typography.Text type="secondary">商品中心 / 商品列表 / 编辑商品</Typography.Text>
          <div className={styles.titleLine}>
            <Typography.Title level={2}>编辑商品</Typography.Title>
            <Tag color="blue">在售</Tag>
          </div>
        </div>
        <div className={styles.headerMeta}>
          <span className={saveState.startsWith('有') ? styles.unsaved : styles.saved}>{saveState}</span>
          <Button>查看买家端</Button>
        </div>
      </div>

      <nav className={styles.sectionNav} aria-label="商品编辑分区">
        {sections.map(([id, label]) => (
          <button
            className={activeSection === id ? styles.activeNav : ''}
            key={id}
            onClick={() => {
              setActiveSection(id)
              scrollToSection(id)
            }}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className={styles.editorGrid}>
        <aside className={styles.optimizer}>
          <div className={styles.optimizerTop}>
            <span className={styles.eyebrow}>商品优化助手</span>
            <strong>{score} 分</strong>
            <Progress percent={score} showInfo={false} strokeColor="#145cff" />
            <Typography.Text type="secondary">补全高质量资料，提高搜索曝光与转化。</Typography.Text>
          </div>
          <div className={styles.optimiseTabs}><b>待优化</b><span>已完成</span></div>
          <ul className={styles.taskList}>
            <li className={images.length >= 5 ? styles.done : ''}><i />上传至少 5 张商品图 <em>{images.length}/5</em></li>
            <li className={draft.subtitle.length >= 15 ? styles.done : ''}><i />完善商品卖点 <em>{draft.subtitle.length}/15+</em></li>
            <li className={draft.description.length >= 60 ? styles.done : ''}><i />丰富图文描述 <em>{draft.description.length}/60+</em></li>
            <li><i />添加商品视频 <em>建议</em></li>
          </ul>
          <div className={styles.aiTip}>
            <img src="/brand/icons/image2.5/96/ai-support-red.png" alt="" />
            <div><b>AI 标题建议</b><span>突出使用场景、核心规格与服务保障。</span></div>
          </div>
        </aside>

        <main className={styles.formColumn}>
          <section className={styles.card} id="basic">
            <SectionHeading number="01" title="基本信息" description="买家最先看到的商品内容" />
            <Form layout="vertical" requiredMark="optional">
              <Form.Item label="商品图片" required extra="支持 JPG、PNG，单张不超过 5MB。首图将作为商品封面。">
                <div className={styles.imageGrid}>
                  {images.map((image, index) => (
                    <div className={styles.imageItem} key={`${image.slice(-24)}-${index}`}>
                      <img src={image} alt={`商品图 ${index + 1}`} />
                      {index === 0 && <span>封面</span>}
                      <button type="button" aria-label={`删除商品图 ${index + 1}`} onClick={() => setImages((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button>
                    </div>
                  ))}
                  {images.length < 9 && (
                    <button className={styles.uploadTile} type="button" onClick={() => fileInputRef.current?.click()}>
                      <b>＋</b><span>添加图片</span><small>{images.length}/9</small>
                    </button>
                  )}
                  <input ref={fileInputRef} hidden style={{ display: 'none' }} type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={addImages} />
                </div>
              </Form.Item>
              <Form.Item label="商品名称" required>
                <Input value={draft.name} maxLength={120} showCount onChange={(event) => update('name', event.target.value)} />
              </Form.Item>
              <Form.Item label="商品卖点">
                <Input value={draft.subtitle} maxLength={80} showCount onChange={(event) => update('subtitle', event.target.value)} />
              </Form.Item>
            </Form>
          </section>

          <section className={styles.card} id="attributes">
            <SectionHeading number="02" title="商品属性" description="准确属性有助于搜索匹配与类目推荐" />
            <Row gutter={18}>
              <Col span={12}><Form.Item label="商品类目" required><Select value={categoryId} onChange={(value) => { setCategoryId(value); const selected = products.find((item) => item.categoryId === value); update('category', selected?.categoryName ?? '未分类') }} options={Array.from(new Map(products.filter((item) => item.categoryId).map((item) => [item.categoryId, { value: item.categoryId as string, label: item.categoryName ?? '未分类' }])).values())} /></Form.Item></Col>
              <Col span={12}><Form.Item label="品牌"><Input value={draft.brand} placeholder="数据库尚未配置品牌" onChange={(event) => update('brand', event.target.value)} /></Form.Item></Col>
              <Col span={12}><Form.Item label="保修类型"><Select defaultValue="manufacturer" options={[{ value: 'manufacturer', label: '品牌官方质保' }, { value: 'seller', label: '店铺质保' }]} /></Form.Item></Col>
              <Col span={12}><Form.Item label="保修期"><Select defaultValue="36" options={[{ value: '12', label: '12 个月' }, { value: '24', label: '24 个月' }, { value: '36', label: '36 个月' }]} /></Form.Item></Col>
            </Row>
          </section>

          <section className={styles.card} id="sales">
            <SectionHeading number="03" title="销售资料" description="设置价格、库存与规格组合" />
            <Table
              pagination={false}
              size="middle"
              rowKey="sku"
              dataSource={[{ sku: draft.sellerSku, specification: skuTitle }]}
              columns={[
                { title: '规格', dataIndex: 'specification' },
                { title: '商家 SKU', render: () => <Input value={draft.sellerSku} onChange={(event) => update('sellerSku', event.target.value)} /> },
                { title: '售价', render: () => <InputNumber min={0} prefix="¥" value={draft.price} onChange={(value) => update('price', value ?? 0)} /> },
                { title: '库存', render: () => <InputNumber min={0} value={draft.stock} onChange={(value) => update('stock', value ?? 0)} /> },
              ]}
            />
            <Button className={styles.addVariation}>＋ 添加销售规格</Button>
          </section>

          <section className={styles.card} id="description">
            <SectionHeading number="04" title="商品描述" description="说明功能、服务范围和交付内容" />
            <Form.Item label="详细描述" required>
              <Input.TextArea rows={7} showCount maxLength={5000} value={draft.description} onChange={(event) => update('description', event.target.value)} />
            </Form.Item>
          </section>

          <section className={styles.card} id="shipping">
            <SectionHeading number="05" title="运费与物流" description="准确的包装数据能减少运费误差" />
            <Row gutter={18}>
              <Col span={8}><Form.Item label="重量"><Space.Compact block><InputNumber className={styles.measureInput} min={0} value={draft.weight} onChange={(value) => update('weight', value ?? 0)} /><span className={styles.unit}>kg</span></Space.Compact></Form.Item></Col>
              <Col span={16}><Form.Item label="包裹尺寸"><Space.Compact block><InputNumber placeholder="长" /><span className={styles.unit}>cm</span><InputNumber placeholder="宽" /><span className={styles.unit}>cm</span><InputNumber placeholder="高" /><span className={styles.unit}>cm</span></Space.Compact></Form.Item></Col>
            </Row>
            <Checkbox defaultChecked>使用平台智能运费模板</Checkbox>
          </section>

          <section className={styles.card} id="marketing">
            <SectionHeading number="06" title="营销与其他" description="配置店铺活动和商品状态" />
            <div className={styles.switchRow}><div><b>允许使用店铺优惠券</b><span>结算时自动匹配可用权益</span></div><Switch defaultChecked /></div>
            <Divider />
            <div className={styles.switchRow}><div><b>企业采购阶梯价</b><span>企业认证客户可查看批量采购价格</span></div><Switch /></div>
          </section>
        </main>

        <aside className={styles.previewColumn}>
          <div className={styles.previewCard}>
            <div className={styles.previewHead}><b>买家端预览</b><span>实时更新</span></div>
            <div className={styles.phoneFrame}>
              <div className={styles.phoneBar}><span>‹</span><b>商品详情</b><span>•••</span></div>
              <div className={styles.cover}><img src={cover} alt="商品封面预览" /><span>1/{Math.max(images.length, 1)}</span></div>
              <div className={styles.previewBody}>
                <div className={styles.previewPrice}><b>¥{draft.price.toLocaleString()}</b><del>¥{draft.marketPrice.toLocaleString()}</del></div>
                <h3>{draft.name || '请输入商品名称'}</h3>
                <p>{draft.subtitle || '补充商品卖点，帮助买家快速了解商品。'}</p>
                <div className={styles.deliveryLine}><span>✓ 企业质保</span><span>次日发货</span><span>开具发票</span></div>
                <div className={styles.storeLine}><img src="/brand/icons/image2.5/96/store-red.png" alt="" /><div><b>{storeName}</b><small>数据库认证商家</small></div><Button size="small">进店</Button></div>
              </div>
              <div className={styles.previewActions}><button>客服</button><button>加入采购单</button><button>立即采购</button></div>
            </div>
            <Typography.Text type="secondary">预览仅用于编辑参考，实际展示以买家端为准。</Typography.Text>
          </div>
        </aside>
      </div>

      <footer className={styles.actionBar}>
        <span>商品 ID：{productId}</span>
        <Space>
          <Button onClick={cancelChanges}>取消修改</Button>
          <Button onClick={() => void save('草稿保存')}>保存草稿</Button>
          <Button type="primary" onClick={() => void save('商品更新')}>更新商品</Button>
        </Space>
      </footer>
    </div>
  )
}

function SectionHeading({ number, title, description }: { number: string; title: string; description: string }) {
  return <div className={styles.sectionHeading}><span>{number}</span><div><h2>{title}</h2><p>{description}</p></div></div>
}
