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
  id: string;
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
  { id: "30000000-0000-0000-0000-000000000001", icon: "store", eyebrow: "数字办公", title: "智能协作终端 Pro", description: "4K 会议 · 多屏协同 · 三年质保", price: "6,299", badge: "旗舰新品", tone: "#f1ecff" },
  { id: "30000000-0000-0000-0000-000000000002", icon: "categories", eyebrow: "办公爆品", title: "高性能商用轻薄本 14 英寸", description: "企业批采价 · 三年上门服务", price: "4,699", badge: "直降 500", tone: "#eef3ff" },
  { id: "30000000-0000-0000-0000-000000000003", icon: "package", eyebrow: "仓储常备", title: "工业级工具组合套装", description: "耐用材质 · 48 小时发货", price: "399", badge: "企业专享", tone: "#fff2e5" },
  { id: "30000000-0000-0000-0000-000000000004", icon: "delivery", eyebrow: "高效履约", title: "热敏标签打印机", description: "高速打印 · 多平台兼容", price: "659", tone: "#eaf8f5" },
  { id: "30000000-0000-0000-0000-000000000005", icon: "wallet", eyebrow: "员工福利", title: "精品咖啡机办公套装", description: "含耗材礼包 · 全国联保", price: "1,299", badge: "满减", tone: "#fff3ee" },
  { id: "30000000-0000-0000-0000-000000000006", icon: "aiSupport", eyebrow: "企业服务", title: "AI 智能客服专业版", description: "多渠道接入 · 7×24 小时在线", price: "999", badge: "限时试用", tone: "#edf5ff" },
];

export const hotKeywords = ["商用轻薄本", "打印机", "咖啡机", "会议", "工具套装", "智能客服"];
