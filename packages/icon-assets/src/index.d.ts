export type CommerceIconName =
  | "home"
  | "categories"
  | "search"
  | "cart"
  | "account"
  | "aiSupport"
  | "package"
  | "delivery"
  | "coupon"
  | "wallet"
  | "store"
  | "analytics";

export const commerceIcons: Readonly<Record<CommerceIconName, string>>;
export const commerceIconsLarge: Readonly<Record<CommerceIconName, string>>;
