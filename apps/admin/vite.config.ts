import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  // The production console is served behind the gateway at /support-console/.
  // Keep generated scripts, styles and public assets inside that prefix instead
  // of pointing the browser at the storefront root (/assets, /brand).
  base: '/support-console/',
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('/node_modules/react/') || id.includes('/node_modules/react-dom/')) {
            return 'react'
          }
          if (id.includes('/node_modules/antd/') || id.includes('/node_modules/@ant-design/')) {
            return 'antd'
          }
        },
      },
    },
  },
})
