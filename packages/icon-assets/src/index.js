const base = "/brand/icons/image2.5";
const iconPath = (name) => `${base}/96/${name}-red.png`;

export const commerceIcons = {
  home: iconPath("home"),
  categories: iconPath("categories"),
  search: iconPath("search"),
  cart: iconPath("cart"),
  account: iconPath("account"),
  aiSupport: iconPath("ai-support"),
  package: iconPath("package"),
  delivery: iconPath("delivery"),
  coupon: iconPath("coupon"),
  wallet: iconPath("wallet"),
  store: iconPath("store"),
  analytics: iconPath("analytics"),
};

export const commerceIconsLarge = Object.fromEntries(
  Object.entries(commerceIcons).map(([name, path]) => [name, path.replace("/96/", "/256/")]),
);
