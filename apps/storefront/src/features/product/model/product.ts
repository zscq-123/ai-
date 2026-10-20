import type { CommerceIconName } from "@commerce/icon-assets";

export type Product = {
  id: string;
  merchantId: string;
  categoryId: string;
  name: string;
  subtitle: string | null;
  status: string;
  skuId: string;
  skuCode: string;
  skuTitle: string;
  salePrice: number;
  marketPrice: number | null;
  availableStock: number;
};

export type ProductPresentation = {
  icon: CommerceIconName;
  tone: string;
  category: string;
  highlights: string[];
  specifications: Array<[string, string]>;
};

const presentations: Record<string, ProductPresentation> = {
  "30000000-0000-0000-0000-000000000001": {
    icon: "store", tone: "#f0ecff", category: "电脑办公 / 会议设备",
    highlights: ["4K 超高清会议", "多屏无线协同", "三年企业质保"],
    specifications: [["产品型号", "NOVA-COLLAB-PRO"], ["视频能力", "4K / 30fps"], ["连接方式", "Wi-Fi 6、蓝牙 5.3、USB-C"], ["质保服务", "三年企业上门服务"]],
  },
  "30000000-0000-0000-0000-000000000002": {
    icon: "categories", tone: "#edf3ff", category: "电脑办公 / 商用电脑",
    highlights: ["高性能处理器", "轻至 1.28kg", "三年上门服务"],
    specifications: [["产品型号", "NOVA-LAPTOP-14"], ["内存容量", "16GB"], ["固态硬盘", "1TB"], ["屏幕规格", "14 英寸 2.5K"]],
  },
  "30000000-0000-0000-0000-000000000003": {
    icon: "package", tone: "#fff2e5", category: "工业品 / 五金工具",
    highlights: ["48 件专业配置", "高强度合金钢", "便携分类收纳"],
    specifications: [["产品型号", "NOVA-TOOLS-48"], ["套装数量", "48 件"], ["主要材质", "铬钒合金钢"], ["适用场景", "设备维护、工程安装"]],
  },
  "30000000-0000-0000-0000-000000000004": {
    icon: "delivery", tone: "#eaf8f5", category: "电脑办公 / 办公设备",
    highlights: ["每分钟 180mm", "无线网络连接", "仓储系统兼容"],
    specifications: [["产品型号", "NOVA-PRINT-PRO"], ["打印方式", "热敏打印"], ["打印宽度", "20–108mm"], ["连接方式", "USB、Wi-Fi、蓝牙"]],
  },
  "30000000-0000-0000-0000-000000000005": {
    icon: "wallet", tone: "#fff3ee", category: "员工福利 / 茶饮设备",
    highlights: ["一键现磨咖啡", "含首月耗材", "全国联保服务"],
    specifications: [["产品型号", "NOVA-COFFEE-SET"], ["水箱容量", "1.8L"], ["豆仓容量", "250g"], ["适用人数", "20–40 人办公室"]],
  },
  "30000000-0000-0000-0000-000000000006": {
    icon: "aiSupport", tone: "#edf5ff", category: "企业服务 / 智能客服",
    highlights: ["多渠道统一接入", "企业知识库问答", "7×24 小时在线"],
    specifications: [["服务版本", "专业版年费"], ["接入渠道", "网页、微信、邮件"], ["知识库容量", "10,000 条"], ["人工坐席", "支持无缝转接"]],
  },
};

export function getProductPresentation(productId: string): ProductPresentation {
  return presentations[productId] ?? {
    icon: "package", tone: "#f1f4f8", category: "企业采购 / 精选商品",
    highlights: ["品牌商家直供", "企业专属价格", "平台履约保障"],
    specifications: [["商品编号", productId], ["售后服务", "平台标准售后"], ["配送范围", "中国大陆"]],
  };
}
