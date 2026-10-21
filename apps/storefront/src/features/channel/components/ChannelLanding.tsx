import Link from "next/link";
import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { getProducts } from "@/features/product/api/getProduct";
import { currencyLabel, getProductPresentation } from "@/features/product/model/product";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { ProductImage } from "@/features/product/components/ProductImage";
import type { ChannelConfig } from "../model/channelContent";
import styles from "./channelLanding.module.css";

export async function ChannelLanding({ config }: { config: ChannelConfig }) {
  const products = await getProducts({ categoryId: config.categoryId });

  return (
    <div className={styles.pageShell}>
      <StorefrontHeader activePath={`/${config.slug}`} />
      <main className={styles.channelPage} style={{ "--accent": config.accent, "--soft-tone": config.softTone } as React.CSSProperties}>
        <nav className={styles.breadcrumb}><Link href="/">首页</Link><span>›</span><strong>{config.title}</strong></nav>

        <section className={styles.channelHero}>
          <div className={styles.heroCopy}>
            <span>{config.eyebrow}</span>
            <h1>{config.title}</h1>
            <p>{config.description}</p>
            <div className={styles.heroActions}><a href="#products">立即选购</a><Link href="/merchant/apply">品牌合作 <b>→</b></Link></div>
          </div>
          <div className={styles.heroVisual}>
            <div className={styles.iconStage}><CommerceIcon name={config.icon} size={230} largeSource priority /></div>
            <span className={styles.orbitOne} /><span className={styles.orbitTwo} />
          </div>
          <div className={styles.metrics}>
            {config.metrics.map((metric) => <div key={metric.label}><strong>{metric.value}</strong><span>{metric.label}</span></div>)}
          </div>
        </section>

        <section className={styles.benefitGrid} aria-label="频道服务优势">
          {config.benefits.map((benefit) => <article key={benefit.title}><span><CommerceIcon name={benefit.icon} size={58} largeSource /></span><div><h2>{benefit.title}</h2><p>{benefit.description}</p></div></article>)}
        </section>

        {config.slug === "brands" && (
          <section className={styles.brandWall}>
            <div><span>AUTHORIZED</span><strong>NOVA WORK</strong></div>
            <div><span>OFFICIAL</span><strong>APEX TECH</strong></div>
            <div><span>PARTNER</span><strong>FORTIS PRO</strong></div>
            <div><span>VERIFIED</span><strong>HOME LAB</strong></div>
            <div><span>ENTERPRISE</span><strong>CLOUDWISE</strong></div>
          </section>
        )}

        <section className={styles.catalogSection} id="products">
          <aside className={styles.filterPanel}>
            <div className={styles.filterTitle}><CommerceIcon name="categories" size={30} /><strong>{config.title}分类</strong></div>
            <div className={styles.filterList}>{config.filters.map((filter, index) => <button className={index === 0 ? styles.activeFilter : undefined} type="button" key={filter}>{filter}<span>›</span></button>)}</div>
            <div className={styles.buyerCard}><CommerceIcon name="aiSupport" size={76} largeSource /><strong>需要采购建议？</strong><p>AI 客服可协助选品、询价与售后。</p><button type="button">立即咨询</button></div>
          </aside>

          <div className={styles.catalogContent}>
            <div className={styles.catalogHeading}><div><span>精选商品</span><h2>{config.title}好物推荐</h2></div><p>共 {products.length} 件商品</p></div>
            <div className={styles.sortBar}><span className={styles.selectedSort}>综合排序</span><span>销量</span><span>价格</span><span>上新</span><label><input type="checkbox" /> 仅看有货</label></div>
            {products.length > 0 ? (
              <div className={styles.productGrid}>
                {products.map((product) => {
                  const presentation = getProductPresentation(product.id);
                  return (
                    <article className={styles.productCard} key={product.id}>
                      <Link className={styles.productVisual} href={`/products/${product.id}`} style={{ background: presentation.tone }}>
                        <span>企业专享</span><ProductImage src={product.imageUrls?.[0] ?? product.coverImageUrl} name={product.name} fallback={presentation.icon} size={150} />
                      </Link>
                      <div className={styles.productInfo}>
                        <small>{presentation.category}</small>
                        <h3><Link href={`/products/${product.id}`}>{product.name}</Link></h3>
                        <p>{product.subtitle}</p>
                        <div><span>{currencyLabel(product.currency)}<strong>{product.salePrice.toLocaleString("zh-CN")}</strong><i>起</i></span><Link href={`/products/${product.id}`} aria-label={`选购${product.name}`}><CommerceIcon name="cart" size={27} /></Link></div>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : <div className={styles.emptyState}><CommerceIcon name="package" size={100} largeSource /><h2>商品正在上架</h2><p>该频道商品正在准备中，稍后再来看看。</p></div>}
          </div>
        </section>
      </main>
      <SupportWidget />
    </div>
  );
}
