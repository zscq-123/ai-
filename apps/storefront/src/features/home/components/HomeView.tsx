import Link from "next/link";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { OpenSupportButton } from "@/features/support/components/OpenSupportButton";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { categoryGroups, productItems } from "../model/homeContent";
import { StorefrontHeader } from "./StorefrontHeader";
import { LoginDialog } from "@/features/auth/components/LoginDialog";
import { HeroCarousel } from "./HeroCarousel";
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
              {categoryGroups.map((group, groupIndex) => (
                <div className={styles.categoryItem} key={group.items.join("-")}>
                  <div className={styles.categoryRow}>
                    <span>
                      {group.items.map((item, index) => (
                        <span key={item}>{index > 0 && <i>/</i>}<Link href={`/search?q=${encodeURIComponent(item)}`}>{item}</Link></span>
                      ))}
                    </span>
                    <b>›</b>
                  </div>
                  <section className={styles.megaMenu} aria-label={`${group.items.join("、")}二级分类`}>
                    <div className={styles.megaContent}>
                      <div className={styles.megaTopLinks}>
                        <Link href={`/search?q=${encodeURIComponent(group.items[0])}`}>企业精选 <b>›</b></Link>
                        <Link href={groupIndex % 2 === 0 ? "/enterprise-procurement" : "/brands"}>品牌直供 <b>›</b></Link>
                        <Link href="/search">全部商品 <b>›</b></Link>
                      </div>
                      <div className={styles.megaSections}>
                        {group.sections.map((section) => (
                          <div className={styles.megaSection} key={section.title}>
                            <Link className={styles.megaSectionTitle} href={`/search?q=${encodeURIComponent(section.title)}`}>{section.title}<b>›</b></Link>
                            <div>{section.items.map((item) => <Link href={`/search?q=${encodeURIComponent(item)}`} key={item}>{item}</Link>)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <aside className={styles.megaPromo}>
                      <span><CommerceIcon name={group.icon} size={92} largeSource /></span>
                      <small>ENTERPRISE PICKS</small>
                      <strong>{group.items[0]}采购专区</strong>
                      <p>品牌直供 · 企业专价 · 履约保障</p>
                      <Link href={`/search?q=${encodeURIComponent(group.items[0])}`}>立即选购</Link>
                    </aside>
                  </section>
                </div>
              ))}
            </div>
          </aside>

          <HeroCarousel />

          <aside className={styles.sideRail}>
            <div className={styles.accountCard}>
              <div className={styles.accountLine}>
                <span className={styles.avatar}><CommerceIcon name="account" size={58} priority /></span>
                <div><strong>Hi，欢迎来到 NOVA</strong><p><LoginDialog className={styles.inlineLogin} triggerLabel="登录" /><i /> <Link href="/register">注册</Link></p></div>
              </div>
              <div className={styles.memberBenefits}>
                <Link href="/register">企业新人礼</Link>
                <Link href="/enterprise-procurement">会员中心</Link>
              </div>
              <section className={styles.procurementNews} aria-label="采购快讯">
                <div><strong>采购快讯</strong><Link href="/search">更多 <b>›</b></Link></div>
                <Link href="/enterprise-procurement">企业集采支持统一询价与结算</Link>
                <Link href="/office">办公设备批量采购专场上线</Link>
                <Link href="/merchant/apply">第三方商家入驻通道已开放</Link>
              </section>
              <nav className={styles.serviceLinks} aria-label="会员服务">
                <Link href="/search"><CommerceIcon name="delivery" size={44} largeSource /><span>物流服务</span></Link>
                <OpenSupportButton />
                <Link href="/search?q=%E5%94%AE%E5%90%8E"><CommerceIcon name="package" size={44} largeSource /><span>售后政策</span></Link>
              </nav>
              <section className={styles.paymentOptions} aria-label="企业支付方式">
                <strong>企业支付</strong>
                <div><span>对公转账</span><span>企业月结</span><span>数字人民币</span></div>
              </section>
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
                <Link className={styles.productVisual} href={`/products/${product.id}`} style={{ background: product.tone }}>
                  {product.badge && <span className={styles.productBadge}>{product.badge}</span>}
                  <CommerceIcon name={product.icon} size={150} largeSource />
                </Link>
                <div className={styles.productInfo}>
                  <span className={styles.productEyebrow}>{product.eyebrow}</span>
                  <h3><Link href={`/products/${product.id}`}>{product.title}</Link></h3>
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
