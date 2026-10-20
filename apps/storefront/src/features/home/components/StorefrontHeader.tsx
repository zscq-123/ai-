import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import Link from "next/link";
import { hotKeywords } from "../model/homeContent";
import styles from "./home.module.css";

const utilityLinks = ["我的订单", "我的采购", "企业服务", "客户服务", "网站导航"];
const navItems = ["首页", "企业集采", "工业品", "办公设备", "员工福利", "品牌馆", "商家入驻"];

export function StorefrontHeader() {
  return (
    <header>
      <div className={styles.utilityBar}>
        <div className={styles.utilityInner}>
          <div className={styles.location}><CommerceIcon name="home" size={20} priority />NOVA 首页<span>·</span>中国大陆</div>
          <div className={styles.utilityLinks}>
            <span>您好，请登录</span><a className={styles.register} href="#">免费注册</a>
            {utilityLinks.map((item) => <a href="#" key={item}>{item}</a>)}
          </div>
        </div>
      </div>
      <div className={styles.masthead}>
        <div className={styles.mastheadInner}>
          <Link className={styles.brand} href="/" aria-label="NOVA 企业商城首页">
            <span className={styles.brandMark}>N</span>
            <span className={styles.brandName}>NOVA<small>企业商城</small></span>
          </Link>
          <div className={styles.searchArea}>
            <form className={styles.searchBox} action="/" role="search">
              <CommerceIcon name="search" size={26} priority />
              <input name="query" defaultValue="商用电脑" aria-label="搜索商品" />
              <button type="submit">搜索</button>
            </form>
            <div className={styles.hotWords}>{hotKeywords.map((item) => <a href="#recommend" key={item}>{item}</a>)}</div>
          </div>
          <button className={styles.cartButton} type="button"><CommerceIcon name="cart" size={34} priority /><span>我的采购车</span><b>3</b></button>
        </div>
      </div>
      <nav className={styles.primaryNav} aria-label="商城导航">
        <div className={styles.primaryNavInner}>
          {navItems.map((item, index) => <a className={index === 0 ? styles.navActive : undefined} href={item === "商家入驻" ? "/merchant/apply" : "#"} key={item}>{item}</a>)}
        </div>
      </nav>
    </header>
  );
}
