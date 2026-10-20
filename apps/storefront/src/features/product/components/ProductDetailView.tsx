import Link from "next/link";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import type { Product } from "../model/product";
import { getProductPresentation } from "../model/product";
import { ProductPurchasePanel } from "./ProductPurchasePanel";
import styles from "./productDetail.module.css";

export function ProductDetailView({ product }: { product: Product }) {
  const presentation = getProductPresentation(product.id);
  const discount = product.marketPrice ? Math.round((1 - product.salePrice / product.marketPrice) * 100) : 0;

  return (
    <main className={styles.detailPage}>
      <nav className={styles.breadcrumb} aria-label="面包屑导航">
        <Link href="/">首页</Link><span>›</span><Link href="/#recommend">{presentation.category}</Link><span>›</span><strong>{product.name}</strong>
      </nav>

      <section className={styles.productCard}>
        <div className={styles.gallery}>
          <div className={styles.mainVisual} style={{ background: presentation.tone }}>
            <span className={styles.visualBadge}>企业精选</span>
            <CommerceIcon name={presentation.icon} size={320} largeSource priority />
          </div>
          <div className={styles.thumbnails}>
            {[presentation.icon, "package", "delivery", "coupon"].map((icon, index) => (
              <button className={index === 0 ? styles.activeThumb : undefined} type="button" aria-label={`查看商品图 ${index + 1}`} key={`${icon}-${index}`}>
                <CommerceIcon name={icon as "package"} size={58} largeSource />
              </button>
            ))}
          </div>
          <div className={styles.galleryMeta}><span>♡ 收藏商品</span><span>↗ 分享</span><span>商品编号：{product.skuCode}</span></div>
        </div>

        <div className={styles.productSummary}>
          <div className={styles.summaryBadges}><span>自营</span><span>企业专享</span></div>
          <h1>{product.name}</h1>
          <p className={styles.subtitle}>{product.subtitle}</p>
          <div className={styles.pricePanel}>
            <div className={styles.priceLine}><span>企业价</span><div>¥<strong>{product.salePrice.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</strong></div>{discount > 0 && <em>节省 {discount}%</em>}</div>
            {product.marketPrice && <div className={styles.marketPrice}><span>市场价</span><del>¥{product.marketPrice.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</del></div>}
            <div className={styles.tierPricing}><span>批采阶梯价</span><b>10–49 件 ¥{Math.round(product.salePrice * .97).toLocaleString()}</b><b>50 件以上 ¥{Math.round(product.salePrice * .93).toLocaleString()}</b></div>
          </div>
          <div className={styles.highlightRow}>
            {presentation.highlights.map((highlight, index) => <span key={highlight}><b>0{index + 1}</b>{highlight}</span>)}
          </div>
          <ProductPurchasePanel product={product} />
        </div>
      </section>

      <section className={styles.contentGrid}>
        <aside className={styles.merchantCard}>
          <div className={styles.merchantTitle}><span><CommerceIcon name="store" size={52} largeSource /></span><div><strong>NOVA 数字办公旗舰店</strong><small>平台认证企业商家</small></div></div>
          <div className={styles.merchantScores}><span><b>4.9</b>商品描述</span><span><b>4.8</b>服务响应</span><span><b>4.9</b>履约质量</span></div>
          <div className={styles.merchantActions}><button type="button">联系商家</button><Link href="/">进入店铺</Link></div>
          <div className={styles.merchantInfo}><p>✓ 企业资质已核验</p><p>✓ 平台交易担保</p><p>✓ 售后服务保障</p></div>
        </aside>

        <article className={styles.detailContent}>
          <div className={styles.detailTabs}><strong>商品详情</strong><span>规格参数</span><span>包装与售后</span><span>采购评价</span></div>
          <section className={styles.detailHero} style={{ background: presentation.tone }}>
            <div><span>NOVA ENTERPRISE SELECT</span><h2>{product.name}</h2><p>{product.subtitle}</p></div>
            <CommerceIcon name={presentation.icon} size={220} largeSource />
          </section>
          <section className={styles.specSection}>
            <div className={styles.sectionTitle}><span>01</span><div><h2>规格参数</h2><p>采购决策所需的关键商品信息</p></div></div>
            <dl>{presentation.specifications.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>
          </section>
          <section className={styles.serviceSection}>
            <div className={styles.sectionTitle}><span>02</span><div><h2>企业采购服务</h2><p>从询价到履约，为企业订单提供完整保障</p></div></div>
            <div className={styles.serviceCards}>
              <div><CommerceIcon name="coupon" size={58} largeSource /><strong>专属询价</strong><p>大宗采购可申请项目报价</p></div>
              <div><CommerceIcon name="delivery" size={58} largeSource /><strong>履约可视</strong><p>订单与物流节点全程追踪</p></div>
              <div><CommerceIcon name="aiSupport" size={58} largeSource /><strong>智能服务</strong><p>AI 客服随时解答采购问题</p></div>
            </div>
          </section>
        </article>
      </section>
    </main>
  );
}
