import type { Product } from "@/features/product/model/product";

export const CART_STORAGE_KEY = "nova:cart:v1";
export type CartItem = Pick<Product, "id" | "name" | "skuTitle" | "salePrice" | "availableStock" | "coverImageUrl" | "currency"> & { quantity: number };

export function parseCart(raw: string): CartItem[] {
  try {
    const value = JSON.parse(raw) as unknown;
    return Array.isArray(value) ? value.filter((item): item is CartItem => Boolean(item && typeof item === "object" && "id" in item)) : [];
  } catch { return []; }
}

export function readCart(): CartItem[] { return parseCart(window.localStorage.getItem(CART_STORAGE_KEY) ?? "[]"); }

export function addToCart(product: Product, quantity: number): void {
  const items = readCart();
  const existing = items.find((item) => item.id === product.id);
  const current = { id: product.id, name: product.name, skuTitle: product.skuTitle, salePrice: product.salePrice, availableStock: product.availableStock, coverImageUrl: product.imageUrls?.[0] ?? product.coverImageUrl, currency: product.currency ?? "CNY" };
  if (existing) Object.assign(existing, current, { quantity: Math.min(product.availableStock, existing.quantity + quantity) });
  else items.push({ ...current, quantity: Math.min(product.availableStock, quantity) });
  writeCart(items);
}

export function writeCart(items: CartItem[]): void {
  window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("nova:cart-updated"));
}
