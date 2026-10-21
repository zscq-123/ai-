import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { CartContents } from "@/features/cart/components/CartContents";
import styles from "./cart.module.css";

export default function CartPage() {
  return (
    <div className={styles.page}>
      <StorefrontHeader activePath="/cart" />
      <main className={styles.main}>
        <div className={styles.heading}><div><small>NOVA PROCUREMENT</small><h1>我的购物车</h1></div><span>企业采购商品将在这里统一结算</span></div>
        <CartContents />
      </main>
      <SupportWidget />
    </div>
  );
}
