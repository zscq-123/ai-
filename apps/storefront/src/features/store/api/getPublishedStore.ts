import { getProducts } from "@/features/product/api/getProduct";
import type { PublishedStore, StoreChannel, StorePageData } from "../model/storeDesign";

const commerceApiBaseUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";

export async function getPublishedStore(
  merchantId: string,
  channel: StoreChannel,
): Promise<StorePageData | null> {
  const response = await fetch(
    `${commerceApiBaseUrl}/api/public/stores/${encodeURIComponent(merchantId)}/${channel}`,
    { cache: "no-store" },
  );
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Commerce API returned ${response.status}`);
  const store = (await response.json()) as PublishedStore;
  const products = (await getProducts()).filter((product) => product.merchantId === merchantId);
  return { ...store, products };
}
