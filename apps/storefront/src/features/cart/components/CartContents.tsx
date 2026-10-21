"use client";

import Link from "next/link";
import { useMemo, useSyncExternalStore } from "react";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { ProductImage } from "@/features/product/components/ProductImage";
import { currencyLabel } from "@/features/product/model/product";
import { CART_STORAGE_KEY, parseCart, writeCart, type CartItem } from "../cartStorage";
import styles from "@/app/cart/cart.module.css";

export function CartContents() {
  const cartJson = useSyncExternalStore(
    (onChange) => { window.addEventListener("storage", onChange); window.addEventListener("nova:cart-updated", onChange); return () => { window.removeEventListener("storage", onChange); window.removeEventListener("nova:cart-updated", onChange); }; },
    () => window.localStorage.getItem(CART_STORAGE_KEY) ?? "[]",
    () => "[]",
  );
  const items = useMemo(() => parseCart(cartJson), [cartJson]);
  const totals = useMemo(() => items.reduce<Record<string, number>>((sum, item) => {
    const currency = item.currency ?? "CNY";
    sum[currency] = (sum[currency] ?? 0) + item.salePrice * item.quantity;
    return sum;
  }, {}), [items]);
  const update = (next: CartItem[]) => writeCart(next);
  if (!items.length) return <section className={styles.empty}><span><CommerceIcon name="cart" size={112} largeSource priority /></span><h2>购物车还是空的</h2><p>去挑选商品，支持企业专价、批量采购与统一履约。</p><Link href="/search">去选购商品</Link></section>;
  return <section className={styles.cartCard}><div className={styles.cartRows}>{items.map((item) => <article className={styles.cartRow} key={item.id}>
    <div style={{ width: 68, height: 68 }}><ProductImage src={item.coverImageUrl} name={item.name} size={68} /></div><div><Link href={`/products/${item.id}`}>{item.name}</Link><small>{item.skuTitle}</small></div><strong>{currencyLabel(item.currency)}{Number(item.salePrice).toFixed(2)}</strong>
    <div className={styles.quantity}><button onClick={() => update(items.map((entry) => entry.id === item.id ? { ...entry, quantity: Math.max(1, entry.quantity - 1) } : entry))}>−</button><span>{item.quantity}</span><button onClick={() => update(items.map((entry) => entry.id === item.id ? { ...entry, quantity: Math.min(entry.availableStock, entry.quantity + 1) } : entry))}>+</button></div>
    <button className={styles.remove} onClick={() => update(items.filter((entry) => entry.id !== item.id))}>删除</button>
  </article>)}</div><footer className={styles.summary}><span>共 {items.reduce((sum, item) => sum + item.quantity, 0)} 件</span><div>合计：{Object.entries(totals).map(([currency, total]) => <strong key={currency}>{currencyLabel(currency)}{total.toFixed(2)}</strong>)}<button disabled title="结算功能准备中">去结算</button></div></footer></section>;
}
