import type { CommerceIconName } from "@commerce/icon-assets";

export type CategoryGroup = {
  icon: CommerceIconName;
  items: string[];
  sections: Array<{ title: string; items: string[] }>;
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
  { icon: "categories", items: ["电脑", "办公", "文具用品"], sections: [
    { title: "电脑整机", items: ["商用轻薄本", "台式机", "一体机", "工作站", "服务器"] },
    { title: "办公设备", items: ["打印机", "投影仪", "扫描仪", "会议设备", "碎纸机"] },
    { title: "办公文具", items: ["文件管理", "书写工具", "桌面用品", "财会用品", "办公耗材"] },
  ] },
  { icon: "store", items: ["手机", "运营商", "数码"], sections: [
    { title: "手机通讯", items: ["企业手机", "对讲机", "移动电源", "手机配件", "充电设备"] },
    { title: "智能数码", items: ["平板电脑", "智能手表", "耳机", "摄像设备", "存储设备"] },
  ] },
  { icon: "package", items: ["工业品", "五金机电", "劳保"], sections: [
    { title: "五金工具", items: ["工具套装", "电动工具", "手动工具", "测量工具", "紧固件"] },
    { title: "工业用品", items: ["仪器仪表", "机械配件", "照明设备", "电工电料", "安全标识"] },
    { title: "劳动防护", items: ["安全帽", "防护手套", "工作服", "防护鞋", "口罩面罩"] },
  ] },
  { icon: "home", items: ["家用电器", "厨卫电器"], sections: [
    { title: "环境电器", items: ["空调", "净化器", "加湿器", "风扇", "取暖器"] },
    { title: "厨房电器", items: ["咖啡机", "饮水机", "微波炉", "电水壶", "冰箱"] },
  ] },
  { icon: "wallet", items: ["员工福利", "食品饮料", "礼品"], sections: [
    { title: "员工关怀", items: ["节日礼盒", "生日福利", "健康礼包", "文体用品", "礼品卡"] },
    { title: "食品饮料", items: ["咖啡茶饮", "休闲零食", "粮油调味", "冲调饮品", "饮用水"] },
  ] },
  { icon: "delivery", items: ["清洁用品", "仓储物流", "耗材"], sections: [
    { title: "清洁用品", items: ["清洁工具", "清洁剂", "垃圾袋", "纸品湿巾", "消毒用品"] },
    { title: "仓储包装", items: ["标签耗材", "包装纸箱", "胶带", "货架", "搬运设备"] },
  ] },
  { icon: "analytics", items: ["软件服务", "云产品", "企业服务"], sections: [
    { title: "企业软件", items: ["智能客服", "协同办公", "财税软件", "数据分析", "项目管理"] },
    { title: "云端服务", items: ["云服务器", "企业邮箱", "网络安全", "数据备份", "域名服务"] },
  ] },
  { icon: "home", items: ["家具", "家装", "建材"], sections: [
    { title: "办公家具", items: ["办公桌", "办公椅", "文件柜", "会议桌", "接待家具"] },
    { title: "装修建材", items: ["照明灯具", "电工电料", "卫浴用品", "墙地材料", "门窗五金"] },
  ] },
  { icon: "delivery", items: ["汽车用品", "维修保养"], sections: [
    { title: "车辆用品", items: ["车载电器", "应急装备", "清洁养护", "维修工具", "安全用品"] },
    { title: "车队服务", items: ["保养服务", "轮胎服务", "车辆租赁", "保险服务", "油卡服务"] },
  ] },
  { icon: "coupon", items: ["品牌馆", "采购专区", "企业特价"], sections: [
    { title: "精选会场", items: ["品牌直供", "新品首发", "企业补贴", "大宗采购", "限时特惠"] },
    { title: "采购服务", items: ["专属询价", "账期采购", "合同采购", "批量下单", "采购方案"] },
  ] },
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
