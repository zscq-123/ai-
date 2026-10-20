import { commerceIcons, type CommerceIconName } from '@commerce/icon-assets'

type Props = { name: CommerceIconName; size?: number }

export function CommerceIcon({ name, size = 28 }: Props) {
  return <img aria-hidden="true" alt="" src={commerceIcons[name]} width={size} height={size} />
}
