import Link from "next/link";
import { getProducts } from "@/features/product/api/getProduct";
import { currencyLabel, getProductPresentation } from "@/features/product/model/product";
import { ProductImage } from "@/features/product/components/ProductImage";
import styles from "./home.module.css";

export async function RecommendedProducts() {
  let products;
  try { products = await getProducts(); }
  catch { return <p role="status">商品暂时无法加载，请稍后重试。</p>; }
  if (!products.length) return <p>商品正在准备中，稍后再来看看。</p>;
  return <div className={styles.productGrid}>{products.slice(0, 12).map((product) => {
    const presentation = getProductPresentation(product.id);
    return <article className={styles.productCard} key={product.id}>
      <Link className={styles.productVisual} href={`/products/${product.id}`} style={{ background: presentation.tone }}>
        <ProductImage src={product.imageUrls?.[0] ?? product.coverImageUrl} name={product.name} fallback={presentation.icon} size={240} />
      </Link>
      <div className={styles.productInfo}>
        <span className={styles.productEyebrow}>{presentation.category}</span>
        <h3><Link href={`/products/${product.id}`}>{product.name}</Link></h3>
        <p>{product.subtitle}</p>
        <div className={styles.productFooter}><span>{currencyLabel(product.currency)}<strong>{product.salePrice.toLocaleString("zh-CN")}</strong></span><Link href={`/products/${product.id}`}>选购</Link></div>
      </div>
    </article>;
  })}</div>;
}
