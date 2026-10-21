"use client";

import { useState } from "react";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import { addToCart } from "@/features/cart/cartStorage";
import type { Product } from "../model/product";
import styles from "./productDetail.module.css";

export function ProductPurchasePanel({ product }: { product: Product }) {
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  const changeQuantity = (nextQuantity: number) => {
    setQuantity(Math.max(1, Math.min(product.availableStock, nextQuantity)));
    setAdded(false);
  };

  return (
    <div className={styles.purchasePanel}>
      <div className={styles.optionRow}>
        <span>规格</span>
        <button className={styles.selectedOption} type="button">{product.skuTitle}</button>
      </div>
      <div className={styles.optionRow}>
        <span>配送</span>
        <div className={styles.deliveryText}><strong>全国配送</strong><small>现在下单，预计 48 小时内发货</small></div>
      </div>
      <div className={styles.optionRow}>
        <span>数量</span>
        <div className={styles.quantityControl}>
          <button type="button" onClick={() => changeQuantity(quantity - 1)} disabled={quantity <= 1}>−</button>
          <input aria-label="采购数量" value={quantity} onChange={(event) => changeQuantity(Number(event.target.value) || 1)} />
          <button type="button" onClick={() => changeQuantity(quantity + 1)} disabled={quantity >= product.availableStock}>+</button>
        </div>
        <small className={styles.stock}>库存 {product.availableStock} 件</small>
      </div>
      <div className={styles.buyActions}>
        <button className={styles.buyNow} type="button">立即采购</button>
        <button className={styles.addCart} type="button" onClick={() => { addToCart(product, quantity); setAdded(true); }}><CommerceIcon name="cart" size={30} />加入采购车</button>
      </div>
      {added && <p className={styles.addedNotice} role="status">已将 {quantity} 件商品加入采购车</p>}
      <div className={styles.purchaseAssurance}><span>✓ 正品保障</span><span>✓ 企业发票</span><span>✓ 7 天无理由</span><span>✓ 价格保护</span></div>
    </div>
  );
}
