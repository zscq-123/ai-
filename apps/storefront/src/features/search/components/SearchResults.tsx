import Link from "next/link";
import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { getProducts } from "@/features/product/api/getProduct";
import { getProductPresentation, type Product } from "@/features/product/model/product";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { CommerceIcon } from "@/shared/ui/CommerceIcon";
import styles from "./search.module.css";

type SearchResultsProps = {
  searchParams: Promise<{ q?: string | string[] }>;
};

export async function SearchResults({ searchParams }: SearchResultsProps) {
  const params = await searchParams;
  const rawQuery = Array.isArray(params.q) ? params.q[0] : params.q;
  const query = rawQuery?.trim().slice(0, 80) ?? "";
  let products: Product[] = [];
  let unavailable = false;

  try {
    products = await getProducts({ query });
  } catch {
    unavailable = true;
  }

  return (
    <div className={styles.pageShell}>
      <StorefrontHeader activePath="" searchQuery={query} />
      <main className={styles.searchPage}>
        <nav className={styles.breadcrumb} aria-label="面包屑导航">
          <Link href="/">首页</Link><span>›</span><strong>商品搜索</strong>
        </nav>

        <section className={styles.summary}>
          <div className={styles.summaryIcon}><CommerceIcon name="search" size={62} largeSource /></div>
          <div>
            <span>{query ? "SEARCH RESULTS" : "PRODUCT DISCOVERY"}</span>
            <h1>{query ? <>“{query}” 的搜索结果</> : "发现企业采购好物"}</h1>
            <p>{unavailable ? "商品服务暂时不可用，请稍后重试。" : query ? `找到 ${products.length} 件相关商品` : `为你推荐 ${products.length} 件精选商品`}</p>
          </div>
        </section>

        {!unavailable && products.length > 0 ? (
          <>
            <div className={styles.toolbar}>
              <div><button className={styles.activeSort} type="button">综合排序</button><button type="button">销量</button><button type="button">价格</button><button type="button">上新</button></div>
              <span>共 <strong>{products.length}</strong> 件商品</span>
            </div>
            <section className={styles.productGrid} aria-label="搜索结果">
              {products.map((product, index) => {
                const presentation = getProductPresentation(product.id);
                return (
                  <article className={styles.productCard} key={product.id}>
                    <Link className={styles.productVisual} href={`/products/${product.id}`} style={{ background: presentation.tone }}>
                      <span>企业专享</span>
                      <CommerceIcon name={presentation.icon} size={176} largeSource priority={index === 0} />
                    </Link>
                    <div className={styles.productInfo}>
                      <small>{presentation.category}</small>
                      <h2><Link href={`/products/${product.id}`}>{product.name}</Link></h2>
                      <p>{product.subtitle || product.skuTitle}</p>
                      <div className={styles.stockLine}><span>现货</span><em>库存 {product.availableStock}</em></div>
                      <div className={styles.priceLine}>
                        <span>¥<strong>{product.salePrice.toLocaleString("zh-CN")}</strong><i>起</i></span>
                        <Link href={`/products/${product.id}`} aria-label={`查看${product.name}详情`}><CommerceIcon name="cart" size={27} /></Link>
                      </div>
                    </div>
                  </article>
                );
              })}
            </section>
          </>
        ) : (
          <section className={styles.emptyState}>
            <CommerceIcon name={unavailable ? "aiSupport" : "package"} size={118} largeSource />
            <h2>{unavailable ? "商品服务暂时不可用" : "没有找到相关商品"}</h2>
            <p>{unavailable ? "请稍后刷新页面，我们正在恢复商品服务。" : "换一个更简短的商品名称或型号试试。"}</p>
            <div>
              <Link href="/search?q=打印机">搜索打印机</Link>
              <Link href="/search?q=会议">搜索会议设备</Link>
              <Link href="/">返回首页</Link>
            </div>
          </section>
        )}
      </main>
      <SupportWidget />
    </div>
  );
}
