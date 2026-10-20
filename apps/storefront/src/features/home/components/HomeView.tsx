import Image from "next/image";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { categoryGroups, channelItems, productItems } from "../model/homeContent";
import { StorefrontHeader } from "./StorefrontHeader";
import styles from "./home.module.css";

const serviceItems = [
  { icon: "package" as const, title: "企业集采", description: "一站式采购管理" },
  { icon: "coupon" as const, title: "专属价格", description: "协议价自动匹配" },
  { icon: "delivery" as const, title: "极速履约", description: "核心城市次日达" },
  { icon: "aiSupport" as const, title: "智能客服", description: "7×24 小时在线" },
];

export function HomeView() {
  return (
    <div className={styles.pageShell}>
      <StorefrontHeader />
      <main>
        <section className={styles.marketplace} aria-label="商品分类和活动推荐">
          <aside className={styles.categoryPanel}>
            <div className={styles.panelTitle}><CommerceIcon name="categories" size={30} priority /><strong>全部商品分类</strong></div>
            <div className={styles.categoryList}>
              {categoryGroups.map((group) => (
                <a className={styles.categoryRow} href="#recommend" key={group.items.join("-")}>
                  <CommerceIcon name={group.icon} size={27} />
                  <span>{group.items.map((item, index) => <span key={item}>{index > 0 && <i>/</i>}{item}</span>)}</span>
                  <b>›</b>
                </a>
              ))}
            </div>
          </aside>

          <section className={styles.heroBanner}>
            <Image className={styles.heroImage} src="/brand/banners/nova-enterprise-hero.png" alt="NOVA 企业采购精选办公与数码商品" fill priority sizes="(max-width: 900px) 100vw, 60vw" />
            <div className={styles.heroShade} />
            <div className={styles.heroCopy}>
              <span className={styles.heroTag}>NOVA 企业采购季</span>
              <h1>企业焕新，<br />采购更省心</h1>
              <p>品牌直供 · 批量优惠 · 极速履约</p>
              <a href="#recommend">立即采购 <span>→</span></a>
            </div>
            <div className={styles.sliderDots} aria-label="轮播图第 1 张"><b /><span /><span /><span /></div>
          </section>

          <aside className={styles.sideRail}>
            <div className={styles.accountCard}>
              <div className={styles.accountLine}><span className={styles.avatar}><CommerceIcon name="account" size={48} priority /></span><div><strong>Hi，欢迎来到 NOVA</strong><p>登录享受企业专属价格</p></div></div>
              <div className={styles.accountActions}><button type="button">立即登录</button><a href="/merchant/apply">商家入驻</a></div>
              <div className={styles.accountStats}><span><b>0</b>待付款</span><span><b>0</b>待收货</span><span><b>12</b>优惠券</span></div>
            </div>
            <div className={styles.channelStack}>
              {channelItems.slice(0, 3).map((item) => <a className={`${styles.channelCard} ${styles[item.tone]}`} href="#recommend" key={item.title}><div><strong>{item.title}</strong><span>{item.description}</span></div><CommerceIcon name={item.icon} size={62} largeSource /></a>)}
            </div>
          </aside>
        </section>

        <section className={styles.serviceStrip} aria-label="商城服务保障">
          {serviceItems.map((item) => <div key={item.title}><span><CommerceIcon name={item.icon} size={50} largeSource /></span><p><strong>{item.title}</strong><small>{item.description}</small></p></div>)}
        </section>

        <section className={styles.recommendSection} id="recommend">
          <div className={styles.sectionHeading}>
            <div><span className={styles.headingIcon}><CommerceIcon name="store" size={38} largeSource /></span><h2>为你推荐</h2><p>精选好物 · 企业采购更划算</p></div>
            <a href="#">查看更多 <span>→</span></a>
          </div>
          <div className={styles.productGrid}>
            {productItems.map((product) => (
              <article className={styles.productCard} key={product.title}>
                <a className={styles.productVisual} href="#" style={{ background: product.tone }}>
                  {product.badge && <span className={styles.productBadge}>{product.badge}</span>}
                  <CommerceIcon name={product.icon} size={150} largeSource />
                </a>
                <div className={styles.productInfo}>
                  <span className={styles.productEyebrow}>{product.eyebrow}</span>
                  <h3>{product.title}</h3>
                  <p>{product.description}</p>
                  <div className={styles.productFooter}><span>¥<strong>{product.price}</strong><small>起</small></span><button type="button" aria-label={`将${product.title}加入采购车`}><CommerceIcon name="cart" size={28} /></button></div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
      <SupportWidget />
    </div>
  );
}
