"use client";

import { CommerceIcon } from "@/shared/ui/CommerceIcon";

export function OpenSupportButton() {
  return (
    <button type="button" onClick={() => window.dispatchEvent(new Event("nova:open-support"))}>
      <CommerceIcon name="aiSupport" size={44} largeSource />
      <span>客户服务</span>
    </button>
  );
}
