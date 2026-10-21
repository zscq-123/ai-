import Link from "next/link";

export default function StoreNotFound() {
  return <main style={{ minHeight: "70vh", display: "grid", placeItems: "center", textAlign: "center" }}><div><h1>店铺尚未发布</h1><p>商家的店铺页正在装修中。</p><Link href="/">返回商城首页</Link></div></main>;
}
