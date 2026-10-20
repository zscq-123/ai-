import type { CommerceIconName } from "@commerce/icon-assets";

export type ChannelSlug = "enterprise-procurement" | "industrial" | "office" | "employee-benefits" | "brands";

export type ChannelConfig = {
  slug: ChannelSlug;
  eyebrow: string;
  title: string;
  description: string;
  icon: CommerceIconName;
  categoryId?: string;
  accent: string;
  softTone: string;
  metrics: Array<{ value: string; label: string }>;
  benefits: Array<{ icon: CommerceIconName; title: string; description: string }>;
  filters: string[];
};

export const channels: Record<ChannelSlug, ChannelConfig> = {
  "enterprise-procurement": {
    slug: "enterprise-procurement",
    eyebrow: "NOVA BUSINESS",
    title: "企业集采",
    description: "集中采购、统一结算、全程可视，为企业降低采购成本与管理复杂度。",
    icon: "package",
    accent: "#c91523",
    softTone: "#fff0ef",
    metrics: [{ value: "12,000+", label: "精选企业商品" }, { value: "15%", label: "平均采购降本" }, { value: "98.7%", label: "订单准时履约" }],
    benefits: [
      { icon: "coupon", title: "协议价格", description: "企业合同价自动匹配" },
      { icon: "analytics", title: "预算管控", description: "部门额度与审批可视" },
      { icon: "delivery", title: "统一履约", description: "多地址配送统一管理" },
    ],
    filters: ["全部商品", "办公集采", "工业物资", "员工福利", "企业服务"],
  },
  industrial: {
    slug: "industrial",
    eyebrow: "INDUSTRIAL SUPPLY",
    title: "工业品",
    description: "覆盖工具、劳保、仓储与维修耗材，满足企业生产经营的高频采购需求。",
    icon: "package",
    categoryId: "10000000-0000-0000-0000-000000000002",
    accent: "#d35a13",
    softTone: "#fff3e8",
    metrics: [{ value: "48h", label: "常备品极速发货" }, { value: "100%", label: "企业资质核验" }, { value: "30 天", label: "项目账期支持" }],
    benefits: [
      { icon: "package", title: "正品工业品", description: "品牌授权渠道供货" },
      { icon: "delivery", title: "仓配直发", description: "核心仓库现货履约" },
      { icon: "aiSupport", title: "选型支持", description: "专业客服辅助选型" },
    ],
    filters: ["全部工业品", "五金工具", "劳保用品", "仓储物流", "维修耗材"],
  },
  office: {
    slug: "office",
    eyebrow: "SMART OFFICE",
    title: "办公设备",
    description: "从智能终端到会议协作设备，一站配齐企业数字化办公所需。",
    icon: "categories",
    categoryId: "10000000-0000-0000-0000-000000000001",
    accent: "#245bd6",
    softTone: "#edf3ff",
    metrics: [{ value: "3 年", label: "企业上门质保" }, { value: "24h", label: "重点城市发货" }, { value: "1 对 1", label: "专属采购顾问" }],
    benefits: [
      { icon: "categories", title: "场景化选品", description: "按岗位与团队规模推荐" },
      { icon: "store", title: "品牌直供", description: "新品与商用型号齐全" },
      { icon: "delivery", title: "安装交付", description: "送装调试一体化服务" },
    ],
    filters: ["全部办公设备", "商用电脑", "会议设备", "打印设备", "办公耗材"],
  },
  "employee-benefits": {
    slug: "employee-benefits",
    eyebrow: "EMPLOYEE BENEFITS",
    title: "员工福利",
    description: "节日关怀、日常激励与积分兑换，让企业福利更有温度、更易管理。",
    icon: "wallet",
    categoryId: "10000000-0000-0000-0000-000000000003",
    accent: "#b76a17",
    softTone: "#fff6e8",
    metrics: [{ value: "200+", label: "知名品牌选择" }, { value: "全国", label: "多地址配送" }, { value: "灵活", label: "额度与套餐配置" }],
    benefits: [
      { icon: "wallet", title: "弹性福利", description: "员工自主兑换心仪商品" },
      { icon: "coupon", title: "节日方案", description: "多档预算快速组合" },
      { icon: "delivery", title: "分址配送", description: "全国员工一键送达" },
    ],
    filters: ["全部福利", "办公茶饮", "节日礼盒", "数码好物", "健康生活"],
  },
  brands: {
    slug: "brands",
    eyebrow: "AUTHORIZED BRANDS",
    title: "品牌馆",
    description: "严选企业级品牌与官方授权商家，获得稳定供货、正品保障和统一售后。",
    icon: "store",
    accent: "#6d4bc3",
    softTone: "#f4efff",
    metrics: [{ value: "100%", label: "授权资质核验" }, { value: "30+", label: "行业品牌伙伴" }, { value: "统一", label: "企业售后入口" }],
    benefits: [
      { icon: "store", title: "官方授权", description: "品牌资质平台核验" },
      { icon: "coupon", title: "品牌专价", description: "企业型号专属优惠" },
      { icon: "aiSupport", title: "统一售后", description: "平台协调服务进度" },
    ],
    filters: ["全部品牌", "数字办公", "工业制造", "员工生活", "企业服务"],
  },
};
