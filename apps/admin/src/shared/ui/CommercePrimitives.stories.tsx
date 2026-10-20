import type { Meta, StoryObj } from '@storybook/react-vite'
import { EmptyState, Price, ProductCard, SkuSelector } from './CommercePrimitives'

const meta = { title: 'Design System/Commerce Components' } satisfies Meta
export default meta
type Story = StoryObj<typeof meta>

export const Product: Story = { render: () => <ProductCard /> }
export const PriceDisplay: Story = { render: () => <Price value={6299} original={6999} /> }
export const Sku: Story = { render: () => <SkuSelector values={['标准版', '专业版', '企业版']} selected="专业版" /> }
export const Empty: Story = { render: () => <EmptyState /> }
