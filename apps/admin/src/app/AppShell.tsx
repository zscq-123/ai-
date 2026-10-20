import { Avatar, Badge, Button, ConfigProvider, Input, Layout, Menu, Space, Typography } from 'antd'
import { useState } from 'react'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { MerchantReviewPage } from '../features/merchants/MerchantReviewPage'
import { CommerceIcon } from '../shared/ui/CommerceIcon'
import styles from './appShell.module.css'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: 'dashboard', icon: <CommerceIcon name="analytics" />, label: '经营概览' },
  { key: 'products', icon: <CommerceIcon name="package" />, label: '商品中心' },
  { key: 'orders', icon: <CommerceIcon name="delivery" />, label: '订单履约' },
  { key: 'marketing', icon: <CommerceIcon name="coupon" />, label: '营销权益' },
  { key: 'customers', icon: <CommerceIcon name="account" />, label: '客户管理' },
  { key: 'support', icon: <CommerceIcon name="aiSupport" />, label: 'AI 客服' },
  { key: 'merchants', icon: <CommerceIcon name="store" />, label: '商家入驻审核' },
]

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [current, setCurrent] = useState('dashboard')
  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#145cff', borderRadius: 12, colorBgLayout: '#f6f8fb', fontFamily: 'Inter, PingFang SC, Microsoft YaHei, sans-serif' }, components: { Menu: { itemHeight: 50, itemBorderRadius: 12, itemSelectedBg: '#eef5ff' } } }}>
      <Layout className={styles.shell}>
        <Sider className={styles.sider} width={236} collapsedWidth={82} collapsible collapsed={collapsed} onCollapse={setCollapsed} trigger={null}>
          <div className={styles.brand}><span>N</span>{!collapsed && <div><strong>NOVA</strong><small>COMMERCE OPS</small></div>}</div>
          <Menu mode="inline" selectedKeys={[current]} onClick={({ key }) => setCurrent(key)} items={menuItems} className={styles.menu} />
          <button className={styles.collapse} onClick={() => setCollapsed((value) => !value)}>{collapsed ? '→' : '收起导航  ←'}</button>
        </Sider>
        <Layout>
          <Header className={styles.header}>
            <Input.Search className={styles.search} placeholder="搜索订单、商品或客户" />
            <Space size={18}>
              <Badge dot><Button type="text" className={styles.headerIcon}><CommerceIcon name="aiSupport" size={31} /></Button></Badge>
              <div className={styles.divider} />
              <Avatar style={{ background: '#07101f' }}>YY</Avatar>
              <div className={styles.user}><Typography.Text strong>运营管理员</Typography.Text><Typography.Text type="secondary">总部运营中心</Typography.Text></div>
            </Space>
          </Header>
          <Content className={styles.content}>{current === 'merchants' ? <MerchantReviewPage /> : <DashboardPage />}</Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  )
}
