import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { getCurrentCustomer } from "@/features/auth/api/getCurrentCustomer";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { LoginDialog } from "@/features/auth/components/LoginDialog";
import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";
import { hotKeywords } from "../model/homeContent";
import styles from "./home.module.css";

const utilityLinks = ["我的订单", "我的采购", "企业服务", "客户服务", "网站导航"];
const navItems = [
  { label: "首页", href: "/" },
  { label: "企业集采", href: "/enterprise-procurement" },
  { label: "工业品", href: "/industrial" },
  { label: "办公设备", href: "/office" },
  { label: "员工福利", href: "/employee-benefits" },
  { label: "品牌馆", href: "/brands" },
  { label: "商家入驻", href: "/merchant/apply" },
];

async function HeaderAccount() {
  const customer = await getCurrentCustomer();
  return customer
    ? <><span>您好，{customer.displayName}</span><LogoutButton /></>
    : <><LoginDialog /><Link className={styles.register} href="/register">免费注册</Link></>;
}

export function StorefrontHeader({ activePath = "/", searchQuery = "" }: { activePath?: string; searchQuery?: string }) {
  return (
    <header>
      <div className={styles.utilityBar}>
        <div className={styles.utilityInner}>
          <div className={styles.location}><CommerceIcon name="home" size={20} priority />NOVA 首页<span>·</span>中国大陆</div>
          <div className={styles.utilityLinks}>
            <Suspense fallback={<><LoginDialog /><Link className={styles.register} href="/register">免费注册</Link></>}><HeaderAccount /></Suspense>
            {utilityLinks.map((item) => <a href="#" key={item}>{item}</a>)}
          </div>
        </div>
      </div>
      <div className={styles.masthead}>
        <div className={styles.mastheadInner}>
          <Link className={styles.brand} href="/" aria-label="NOVA 企业商城首页">
            <Image className={styles.brandMark} src="/brand/logo/nova-mark-image2.5-v1.png" alt="" width={62} height={62} priority />
            <span className={styles.brandName}>NOVA<small>企业商城</small></span>
          </Link>
          <div className={styles.searchArea}>
            <form className={styles.searchBox} action="/search" method="get" role="search">
              <CommerceIcon name="search" size={26} priority />
              <input name="q" defaultValue={searchQuery} placeholder="搜索商品名称、型号或服务" aria-label="搜索商品" />
              <button type="submit">搜索</button>
            </form>
            <div className={styles.hotWords}>{hotKeywords.map((item) => <Link href={`/search?q=${encodeURIComponent(item)}`} key={item}>{item}</Link>)}</div>
          </div>
        </div>
      </div>
      <nav className={styles.primaryNav} aria-label="商城导航">
        <div className={styles.primaryNavInner}>
          {navItems.map((item) => <Link className={activePath === item.href ? styles.navActive : undefined} href={item.href} key={item.href}>{item.label}</Link>)}
        </div>
      </nav>
    </header>
  );
}
