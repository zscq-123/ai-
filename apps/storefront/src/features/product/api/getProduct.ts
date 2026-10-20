import type { Product } from "../model/product";

const commerceApiBaseUrl = process.env.COMMERCE_API_BASE_URL ?? "http://127.0.0.1:8080";

export async function getProduct(productId: string): Promise<Product | null> {
  const response = await fetch(`${commerceApiBaseUrl}/api/public/products/${encodeURIComponent(productId)}`, {
    cache: "no-store",
  });

  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Commerce API returned ${response.status}`);
  return response.json() as Promise<Product>;
}
