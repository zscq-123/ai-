import { Button } from 'antd'
import { CommerceIcon } from './CommerceIcon'
import styles from './commercePrimitives.module.css'

export function Price({ value, original }: { value: number; original?: number }) {
  return <div className={styles.price}><small>¥</small><strong>{value.toLocaleString('zh-CN')}</strong>{original && <del>¥{original.toLocaleString('zh-CN')}</del>}</div>
}

export function SkuSelector({ values, selected }: { values: string[]; selected: string }) {
  return <div className={styles.skus}>{values.map((value) => <button className={value === selected ? styles.selected : undefined} key={value}>{value}</button>)}</div>
}

export function ProductCard() {
  return <article className={styles.productCard}><div className={styles.productImage}><CommerceIcon name="package" size={112} /></div><span className={styles.tag}>企业专享</span><h3>智能协作终端 Pro</h3><p>4K 会议 · 多屏协同 · 三年质保</p><Price value={6299} original={6999} /><Button type="primary" block>加入采购单</Button></article>
}

export function EmptyState() {
  return <div className={styles.empty}><CommerceIcon name="search" size={86} /><h3>没有找到匹配商品</h3><p>换一个关键词，或联系 AI 客服帮你寻找。</p><Button>清除筛选条件</Button></div>
}
