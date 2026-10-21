"use client";

import { useState } from "react";
import type { Product, ProductPresentation } from "../model/product";
import { ProductImage } from "./ProductImage";
import styles from "./productDetail.module.css";

export function ProductGallery({ product, presentation }: { product: Product; presentation: ProductPresentation }) {
  const images = product.imageUrls?.length ? product.imageUrls : product.coverImageUrl ? [product.coverImageUrl] : [];
  const [selection, setSelection] = useState(0);
  const current = Math.min(selection, Math.max(0, images.length - 1));
  return <div className={styles.gallery}>
    <div className={`${styles.mainVisual} ${images.length ? styles.photoVisual : ""}`} style={{ background: images.length ? "#fff" : presentation.tone }}>
      <ProductImage src={images[current]} name={`${product.name} 商品图 ${current + 1}`} fallback={presentation.icon} size={520} priority />
    </div>
    {images.length > 1 && <div className={styles.photoThumbnails} aria-label="商品图片">
      {images.map((src, index) => <button type="button" key={`${src}-${index}`} aria-label={`查看商品图 ${index + 1}`} aria-pressed={index === current}
        className={index === current ? styles.activeThumb : undefined} onClick={() => setSelection(index)}>
        <ProductImage src={src} name={`${product.name} 缩略图 ${index + 1}`} size={72} />
      </button>)}
    </div>}
    <div className={styles.galleryMeta}><span>{images.length ? `${current + 1} / ${images.length}` : "商家暂未上传商品图片"}</span><span>商品编号：{product.skuCode}</span></div>
  </div>;
}
