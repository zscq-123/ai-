import type { Preview } from '@storybook/react-vite'
import '../src/index.css'

const preview: Preview = {
  parameters: {
    layout: 'padded',
    a11y: { test: 'todo' },
    backgrounds: { options: { light: { name: '浅色', value: '#f6f8fb' }, dark: { name: '深色', value: '#07101f' } } },
  },
}

export default preview
