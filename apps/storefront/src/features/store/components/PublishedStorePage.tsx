import Link from "next/link";
import type { CSSProperties } from "react";
import type { StorePageData } from "../model/storeDesign";
import styles from "./publishedStore.module.css";

export function PublishedStorePage({ store }: { store: StorePageData }) {
  const variables = {
    "--store-primary": store.config.theme.primaryColor,
    "--store-background": store.config.theme.backgroundColor,
    "--store-text": store.config.theme.textColor,
  } as CSSProperties;
  const visible = store.config.modules.filter((module) => module.visible);

  return <main className={`${styles.store} ${store.channel === "MOBILE" ? styles.mobile : ""}`} style={variables}>
    {visible.map((module) => {
      if (module.type === "BANNER") return <section className={styles.banner} key={module.id} style={module.data.imageUrl ? { backgroundImage: `linear-gradient(90deg, rgb(0 0 0 / 62%), rgb(0 0 0 / 8%)), url(${module.data.imageUrl})` } : undefined}><div><small>{store.storeName}</small><h1>{module.data.title}</h1><p>{module.data.subtitle}</p></div></section>;
      if (module.type === "STORE_INFO") return <section className={styles.profile} key={module.id}><span>{(module.data.title ?? store.storeName).slice(0, 1)}</span><div><h2>{module.data.title ?? store.storeName}</h2><p>{module.data.description}</p></div><strong>已认证商家</strong></section>;
      if (module.type === "ANNOUNCEMENT") return <section className={styles.notice} key={module.id}><b>店铺公告</b><p>{module.data.text}</p></section>;
      if (module.type === "COUPON") return <section className={styles.coupon} key={module.id}><div><small>店铺优惠</small><h2>{module.data.title}</h2><p>{module.data.description}</p></div><button type="button">立即领取</button></section>;
      const products = store.products.slice(0, module.data.limit ?? 6);
      return <section className={styles.products} key={module.id}><div className={styles.sectionTitle}><h2>{module.data.title ?? "店铺精选"}</h2><span>{products.length} 件商品</span></div><div className={styles.productGrid}>{products.map((product) => <Link href={`/products/${product.id}`} key={product.id}><div className={styles.productVisual}><span>NOVA</span></div><h3>{product.name}</h3><p>{product.subtitle}</p><strong>¥{product.salePrice.toFixed(2)}</strong></Link>)}</div>{products.length === 0 && <p className={styles.empty}>店铺暂无在售商品</p>}</section>;
    })}
    <footer className={styles.footer}><b>{store.storeName}</b><span>店铺页版本 {store.version}</span></footer>
  </main>;
}
