import Image from "next/image";
import { commerceIcons, commerceIconsLarge, type CommerceIconName } from "@commerce/icon-assets";

type CommerceIconProps = {
  name: CommerceIconName;
  size?: number;
  priority?: boolean;
  largeSource?: boolean;
  className?: string;
};

export function CommerceIcon({ name, size = 32, priority = false, largeSource = false, className }: CommerceIconProps) {
  const source = largeSource ? commerceIconsLarge[name] : commerceIcons[name];
  return <Image aria-hidden="true" className={className} src={source} alt="" width={size} height={size} priority={priority} />;
}
