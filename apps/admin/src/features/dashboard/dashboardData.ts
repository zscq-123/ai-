import type { CommerceIconName } from '@commerce/icon-assets'

export const metrics: Array<{ label: string; value: string; change: string; icon: CommerceIconName }> = [
  { label: '今日交易额', value: '¥ 286,430', change: '+18.6%', icon: 'wallet' },
  { label: '待履约订单', value: '1,284', change: '+6.2%', icon: 'package' },
  { label: '新增企业客户', value: '86', change: '+12.4%', icon: 'account' },
  { label: 'AI 服务解决率', value: '92.8%', change: '+3.1%', icon: 'aiSupport' },
]

export const orders = [
  { id: 'NO202610200018', customer: '远景科技（上海）有限公司', amount: '¥ 18,620', status: '待发货' },
  { id: 'NO202610200017', customer: '华北智造供应链集团', amount: '¥ 76,800', status: '审批中' },
  { id: 'NO202610200016', customer: '城市创新研究院', amount: '¥ 9,460', status: '已完成' },
]
