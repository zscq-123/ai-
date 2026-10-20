const base = "/brand/icons/image2.5";

export const commerceIcons = {
  home: `${base}/96/home.png`,
  categories: `${base}/96/categories.png`,
  search: `${base}/96/search.png`,
  cart: `${base}/96/cart.png`,
  account: `${base}/96/account.png`,
  aiSupport: `${base}/96/ai-support.png`,
  package: `${base}/96/package.png`,
  delivery: `${base}/96/delivery.png`,
  coupon: `${base}/96/coupon.png`,
  wallet: `${base}/96/wallet.png`,
  store: `${base}/96/store.png`,
  analytics: `${base}/96/analytics.png`,
};

export const commerceIconsLarge = Object.fromEntries(
  Object.entries(commerceIcons).map(([name, path]) => [name, path.replace("/96/", "/256/")]),
);
