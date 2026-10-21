import type { Product } from "@/features/product/model/product";

export type StoreChannel = "WEB" | "MOBILE";
export type StoreModule = {
  id: string;
  type: "BANNER" | "STORE_INFO" | "PRODUCT_GRID" | "ANNOUNCEMENT" | "COUPON";
  visible: boolean;
  data: {
    title?: string;
    subtitle?: string;
    description?: string;
    text?: string;
    imageUrl?: string;
    limit?: number;
  };
};
export type StoreConfig = {
  theme: { primaryColor: string; backgroundColor: string; textColor: string };
  modules: StoreModule[];
};
export type PublishedStore = {
  merchantId: string;
  storeName: string;
  channel: StoreChannel;
  version: number;
  config: StoreConfig;
  publishedAt: string;
};

export type StorePageData = PublishedStore & { products: Product[] };
