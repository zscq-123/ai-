import { Suspense } from "react";
import { headers } from "next/headers";
import { connection } from "next/server";
import { notFound } from "next/navigation";
import { StorefrontHeader } from "@/features/home/components/StorefrontHeader";
import { SupportWidget } from "@/features/support/components/SupportWidget";
import { getPublishedStore } from "@/features/store/api/getPublishedStore";
import { PublishedStorePage } from "@/features/store/components/PublishedStorePage";
import type { StoreChannel } from "@/features/store/model/storeDesign";

async function StoreContent({ params, searchParams }: {
  params: Promise<{ merchantId: string }>;
  searchParams: Promise<{ channel?: string }>;
}) {
  await connection();
  const [{ merchantId }, query, requestHeaders] = await Promise.all([params, searchParams, headers()]);
  const explicitChannel = query.channel?.toLowerCase();
  const mobileUserAgent = /Android|iPhone|iPad|Mobile/i.test(requestHeaders.get("user-agent") ?? "");
  const channel: StoreChannel = explicitChannel === "mobile" || (explicitChannel !== "web" && mobileUserAgent) ? "MOBILE" : "WEB";
  const store = await getPublishedStore(merchantId, channel);
  if (!store) notFound();
  return <><PublishedStorePage store={store} /><SupportWidget merchantId={merchantId} /></>;
}

export default function StorePage(props: {
  params: Promise<{ merchantId: string }>;
  searchParams: Promise<{ channel?: string }>;
}) {
  return <>
    <StorefrontHeader activePath="" />
    <Suspense fallback={<StoreSkeleton />}><StoreContent {...props} /></Suspense>
  </>;
}

function StoreSkeleton() {
  return <main style={{ minHeight: "70vh", display: "grid", placeItems: "center", color: "#6e6e73" }}>正在读取店铺页…</main>;
}
