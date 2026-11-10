import { Suspense } from "react";
import { notFound } from "next/navigation";
import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { getProduct } from "@/features/product/api/getProduct";
import { ProductDetailView } from "@/features/product/components/ProductDetailView";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import styles from "@/features/product/components/productDetail.module.css";

async function ProductContent({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params;
  const product = await getProduct(productId);
  if (!product) notFound();
  return <>
    <ProductDetailView product={product} />
    <SupportWidget merchantId={product.merchantId} productId={product.id} skuId={product.skuId} />
  </>;
}

export default function ProductPage({ params }: { params: Promise<{ productId: string }> }) {
  return (
    <div className={styles.pageShell}>
      <StorefrontHeader activePath="" />
      <Suspense fallback={<ProductDetailSkeleton />}>
        <ProductContent params={params} />
      </Suspense>
    </div>
  );
}

function ProductDetailSkeleton() {
  return (
    <main className={styles.skeleton} aria-label="商品详情加载中">
      <div /><section><span /><span /><span /><span /></section>
    </main>
  );
}
