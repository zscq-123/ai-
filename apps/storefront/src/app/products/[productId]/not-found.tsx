import Link from "next/link";

export default function ProductNotFound() {
  return (
    <main style={{ minHeight: "60vh", display: "grid", placeItems: "center", textAlign: "center", padding: 32 }}>
      <div><h1>商品暂时不可用</h1><p>该商品可能已下架，去首页看看其他企业好物。</p><Link href="/" style={{ color: "#e1251b", fontWeight: 700 }}>返回商城首页</Link></div>
    </main>
  );
}
