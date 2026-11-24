import { lazy, Suspense } from 'react'
import { FluentProvider, Spinner, webLightTheme } from '@fluentui/react-components'

// NOVA 商场运营后台暂时停用；保留源码，后续恢复时重新引入 AppShell 即可。
// import { AppShell } from './app/AppShell'

const SupportConsole = lazy(() => import('./features/support-console/SupportConsole'))

export default function App() {
  return (
    <FluentProvider className="nova-fluent-provider" theme={webLightTheme}>
      <Suspense fallback={<div className="nova-fluent-loading"><Spinner size="small" label="正在打开 NOVA 客服工作台…" /></div>}>
        <SupportConsole />
      </Suspense>
    </FluentProvider>
  )

  // NOVA 商场恢复入口：return <AppShell />
}
