import Link from "next/link";
import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./cart.module.css";

export default function CartPage() {
  return (
    <div className={styles.page}>
      <StorefrontHeader activePath="/cart" />
      <main className={styles.main}>
        <div className={styles.heading}><div><small>NOVA PROCUREMENT</small><h1>我的购物车</h1></div><span>企业采购商品将在这里统一结算</span></div>
        <section className={styles.empty}>
          <span><CommerceIcon name="cart" size={112} largeSource priority /></span>
          <h2>购物车还是空的</h2>
          <p>去挑选商品，支持企业专价、批量采购与统一履约。</p>
          <Link href="/search">去选购商品</Link>
        </section>
      </main>
      <SupportWidget />
    </div>
  );
}
