import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { categoryItems, serviceItems } from "../model/homeContent";
import { StorefrontHeader } from "./StorefrontHeader";
import styles from "./home.module.css";

export function HomeView() {
  return (
    <div>
      <StorefrontHeader />
      <main>
        <section className={styles.hero}>
          <div className={styles.heroContent}>
            <span className={styles.eyebrow}>ENTERPRISE COMMERCE · 2026</span>
            <h1>让企业采购，<br /><em>更聪明一点。</em></h1>
            <p>从寻品、比价、审批到履约，一套面向现代企业的数字化采购体验。</p>
            <div className={styles.heroActions}><a className={styles.primaryButton} href="#categories">开始选购</a><a className={styles.textButton} href="#services">了解企业方案 <span>→</span></a></div>
            <div className={styles.metrics}><div><strong>12,000+</strong><span>精选商品</span></div><div><strong>98.7%</strong><span>准时履约</span></div><div><strong>7×24h</strong><span>智能服务</span></div></div>
          </div>
          <div className={styles.heroVisual} aria-label="智能企业采购服务">
            <div className={styles.orbit} />
            <div className={styles.heroIconMain}><CommerceIcon name="store" size={210} largeSource priority /></div>
            <div className={`${styles.floatingIcon} ${styles.floatOne}`}><CommerceIcon name="analytics" size={76} largeSource /></div>
            <div className={`${styles.floatingIcon} ${styles.floatTwo}`}><CommerceIcon name="aiSupport" size={76} largeSource /></div>
            <span className={styles.statusPill}>● 采购服务在线</span>
          </div>
        </section>
        <section className={styles.section} id="services">
          <div className={styles.sectionHeading}><div><span className={styles.kicker}>核心能力</span><h2>为企业交易全链路而生</h2></div><p>标准化能力与灵活业务规则并存，为每一次采购提供确定性。</p></div>
          <div className={styles.serviceGrid}>{serviceItems.map((item) => <article className={styles.serviceCard} key={item.title}><div className={styles.serviceIcon}><CommerceIcon name={item.icon} size={72} largeSource /></div><div><h3>{item.title}</h3><p>{item.description}</p><span>{item.accent}</span></div></article>)}</div>
        </section>
        <section className={styles.section} id="categories">
          <div className={styles.sectionHeading}><div><span className={styles.kicker}>热门分类</span><h2>高频采购，一站配齐</h2></div><a className={styles.textButton} href="#">查看全部分类 <span>→</span></a></div>
          <div className={styles.categoryGrid}>{categoryItems.map((item, index) => <article className={styles.categoryCard} key={item.label} style={{ background: item.tone }}><div><span>0{index + 1}</span><h3>{item.label}</h3><p>{item.detail}</p></div><CommerceIcon name={item.icon} size={112} largeSource /></article>)}</div>
        </section>
      </main>
      <button className={styles.supportButton} aria-label="联系 AI 客服"><CommerceIcon name="aiSupport" size={48} largeSource /><span>AI 客服</span></button>
    </div>
  );
}
