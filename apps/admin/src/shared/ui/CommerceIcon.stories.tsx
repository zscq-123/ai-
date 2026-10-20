import type { Meta, StoryObj } from '@storybook/react-vite'
import type { CommerceIconName } from '@commerce/icon-assets'
import { CommerceIcon } from './CommerceIcon'

const names: CommerceIconName[] = ['home', 'categories', 'search', 'cart', 'account', 'aiSupport', 'package', 'delivery', 'coupon', 'wallet', 'store', 'analytics']

const meta = {
  title: 'Design System/Image 2.5 Icons',
  component: CommerceIcon,
  args: { name: 'store', size: 72 },
} satisfies Meta<typeof CommerceIcon>

export default meta
type Story = StoryObj<typeof meta>

export const Single: Story = {}

export const Gallery: Story = {
  render: () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(120px, 1fr))', gap: 16 }}>
      {names.map((name) => <div key={name} style={{ padding: 20, display: 'grid', placeItems: 'center', gap: 8, color: '#fff', background: '#07101f', borderRadius: 18 }}><CommerceIcon name={name} size={72} /><span style={{ color: '#94a3b8', fontSize: 12 }}>{name}</span></div>)}
    </div>
  ),
}
