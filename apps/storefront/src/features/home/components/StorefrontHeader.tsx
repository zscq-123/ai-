import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./home.module.css";

const navItems = [{ label: "首页", href: "/" }, { label: "商品分类", href: "/#categories" }, { label: "企业采购", href: "/#services" }, { label: "商家入驻", href: "/merchant/apply" }];

export function StorefrontHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <a className={styles.brand} href="#" aria-label="NOVA 商城首页">
          <span className={styles.brandMark}>N</span><span>NOVA</span><small>企业商城</small>
        </a>
        <nav className={styles.nav} aria-label="主导航">
          {navItems.map((item, index) => <a className={index === 0 ? styles.navActive : undefined} href={item.href} key={item.label}>{item.label}</a>)}
        </nav>
        <div className={styles.headerActions}>
          <button className={styles.iconButton} aria-label="搜索"><CommerceIcon name="search" size={30} priority /></button>
          <button className={styles.iconButton} aria-label="购物车"><CommerceIcon name="cart" size={30} priority /><span className={styles.badge}>3</span></button>
          <button className={styles.accountButton}><CommerceIcon name="account" size={30} priority /><span>企业账户</span></button>
        </div>
      </div>
    </header>
  );
}
