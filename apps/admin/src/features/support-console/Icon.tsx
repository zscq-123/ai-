export type IconName = 'grid' | 'inbox' | 'star' | 'store' | 'mail' | 'spark' | 'settings' | 'help' | 'search' | 'chevron' | 'arrow' | 'plus' | 'bell' | 'check' | 'close' | 'external' | 'refresh' | 'globe' | 'chat' | 'clock' | 'shield' | 'bolt' | 'send' | 'filter' | 'link' | 'logout' | 'menu' | 'trend' | 'file' | 'more'
const paths: Record<IconName, string> = {
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  inbox: 'M4 4h16l2 12v4H2v-4L4 4z M2 15h6l2 3h4l2-3h6',
  star: 'm12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3-5.6-3-5.6 3 1.1-6.3L3 9.6l6.2-.9L12 3z',
  store: 'M4 10v11h16V10 M2 7l2-4h16l2 4v3a3 3 0 0 1-5 2 3 3 0 0 1-5 0 3 3 0 0 1-5 0 3 3 0 0 1-5-2V7z M9 21v-7h6v7',
  mail: 'M3 5h18v14H3z m0 1 9 7 9-7', spark: 'm12 2 2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6L12 2z',
  settings: 'm9 3-1 3-3 1-2 3 2 2-1 3 2 3 3-1 2 3h3l1-3 3-1 2-3-2-2 1-3-2-3-3 1-2-3H9z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  help: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M9 8a3 3 0 0 1 6 1c0 2-3 2-3 4 M12 16v1',
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 m-2 5 6 6', chevron: 'm9 5 7 7-7 7', arrow: 'M4 12h16 m-6-6 6 6-6 6',
  plus: 'M12 5v14 M5 12h14', bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4', check: 'm5 12 4 4L19 6', close: 'm6 6 12 12 M6 18 18 6', external: 'M14 3h7v7 m0-7L10 14 M10 3H3v18h18v-7',
  refresh: 'M20 7a9 9 0 0 0-15-2L2 8 m0-6v6h6 M4 17a9 9 0 0 0 15 2l3-3 m0 6v-6h-6', globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M3 12h18 M12 3c-5 5-5 13 0 18 5-5 5-13 0-18',
  chat: 'M21 11a9 8 0 0 1-9 8H7l-5 3 2-7a8 8 0 1 1 17-4z M8 10h8 M8 14h5', clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 6v6l4 2', shield: 'm12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4z m-5 10 3 3 7-7',
  bolt: 'm13 2-9 12h7l-1 8L21 9h-8V2z', send: 'm3 3 19 9-19 9 4-9-4-9z M7 12h15', filter: 'M3 5h18 M6 12h12 M9 19h6', link: 'm9 15 6-6 M8 16l-2 2a4 4 0 0 1-5-5l5-5a4 4 0 0 1 5 0 M16 8l2-2a4 4 0 0 1 5 5l-5 5a4 4 0 0 1-5 0', logout: 'M9 3H3v18h6 M9 12h12 m-5-5 5 5-5 5', menu: 'M3 6h18 M3 12h18 M3 18h18', trend: 'm3 17 6-6 4 3 8-10 M15 4h6v6', file: 'M4 2h10l6 6v14H4z M14 2v6h6 M8 12h8 M8 16h8', more: 'M4 12h1 M11 12h1 M18 12h1',
}
export function Icon({ name, size = 20, className = '' }: { name: IconName; size?: number; className?: string }) {
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
