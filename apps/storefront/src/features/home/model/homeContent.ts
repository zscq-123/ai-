import type { CommerceIconName } from "@commerce/icon-assets";

export type CategoryGroup = {
  icon: CommerceIconName;
  items: string[];
};

export type ChannelItem = {
  icon: CommerceIconName;
  title: string;
  description: string;
  tone: "mint" | "violet" | "blue" | "amber";
};

export type ProductItem = {
  icon: CommerceIconName;
  eyebrow: string;
  title: string;
  description: string;
  price: string;
  badge?: string;
  tone: string;
};

export const categoryGroups: CategoryGroup[] = [
  { icon: "categories", items: ["电脑", "办公", "文具用品"] },
  { icon: "store", items: ["手机", "运营商", "数码"] },
  { icon: "package", items: ["工业品", "五金机电", "劳保"] },
  { icon: "home", items: ["家用电器", "厨卫电器", "家具"] },
  { icon: "wallet", items: ["员工福利", "食品饮料", "礼品"] },
  { icon: "delivery", items: ["清洁用品", "仓储物流", "耗材"] },
  { icon: "analytics", items: ["软件服务", "云产品", "企业服务"] },
  { icon: "coupon", items: ["采购专区", "品牌馆", "特价"] },
];

export const channelItems: ChannelItem[] = [
  { icon: "coupon", title: "企业补贴", description: "采购立减  满额返券", tone: "mint" },
  { icon: "store", title: "品牌直供", description: "正品保障  极速售后", tone: "violet" },
  { icon: "delivery", title: "次日送达", description: "核心城市  仓配直发", tone: "blue" },
  { icon: "package", title: "工业特惠", description: "大宗采购  阶梯低价", tone: "amber" },
];

export const productItems: ProductItem[] = [
  { icon: "categories", eyebrow: "办公爆品", title: "高性能商用轻薄本 14 英寸", description: "企业批采价 · 三年上门服务", price: "4,699", badge: "直降 500", tone: "#eef3ff" },
  { icon: "store", eyebrow: "数字办公", title: "智能会议终端套装", description: "4K 会议 · AI 降噪 · 快速部署", price: "2,899", badge: "新品", tone: "#f1ecff" },
  { icon: "package", eyebrow: "仓储常备", title: "工业级工具组合套装", description: "耐用材质 · 48 小时发货", price: "399", badge: "企业专享", tone: "#fff2e5" },
  { icon: "delivery", eyebrow: "高效履约", title: "热敏标签打印机", description: "高速打印 · 多平台兼容", price: "659", tone: "#eaf8f5" },
  { icon: "wallet", eyebrow: "员工福利", title: "精品咖啡机办公套装", description: "含耗材礼包 · 全国联保", price: "1,299", badge: "满减", tone: "#fff3ee" },
  { icon: "aiSupport", eyebrow: "企业服务", title: "AI 智能客服专业版", description: "多渠道接入 · 7×24 小时在线", price: "999", badge: "限时试用", tone: "#edf5ff" },
];

export const hotKeywords = ["商用电脑", "办公耗材", "员工福利", "会议设备", "工业工具", "企业服务"];
