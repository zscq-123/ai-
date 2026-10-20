import type { CommerceIconName } from "@commerce/icon-assets";

export type ServiceItem = { icon: CommerceIconName; title: string; description: string; accent: string };

export const serviceItems: ServiceItem[] = [
  { icon: "package", title: "企业集采", description: "阶梯价格与批量下单", accent: "采购效率提升 42%" },
  { icon: "delivery", title: "智慧履约", description: "仓配进度全程可视", accent: "核心城市次日达" },
  { icon: "coupon", title: "专属权益", description: "合同价与采购券统一管理", accent: "权益自动匹配" },
  { icon: "aiSupport", title: "AI 客服", description: "7×24 小时售前售后支持", accent: "平均 3 秒响应" },
];

export const categoryItems = [
  { label: "办公设备", detail: "智能终端 · 打印设备", tone: "#eaf2ff", icon: "categories" as const },
  { label: "工业耗材", detail: "工具 · 安防 · 仓储", tone: "#e9fbf3", icon: "package" as const },
  { label: "员工福利", detail: "生活电器 · 数码好物", tone: "#fff4e8", icon: "wallet" as const },
];
